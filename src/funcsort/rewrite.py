"""Reassemble sorted units back into source code."""

import typing as t

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit, _Statement


def rewrite_module(
    units: list[SortableUnit],
    fixed_nodes: list[_Statement],
    ordered_names: list[str],
    original_body: list[_Statement] | None = None,
    header: str = "",
) -> str:
    """Rewrite a module with functions in the specified order.

    Args:
        units: All sortable units.
        fixed_nodes: Non-sortable nodes to keep in place.
        ordered_names: Unit names in desired order.
        original_body: All top-level statements in original source order, used to
            tell whether two constants were adjacent in the source.
        header: Module header to preserve (e.g., uv script metadata).

    Returns:
        Reformatted source code.
    """
    unit_map = {unit.name: unit for unit in units}
    new_body: list[_Statement] = []

    # Map each original statement to the one that preceded it in the source, so we
    # can tell whether a constant kept its original neighbour (and thus its original
    # blank-line separation) or was moved next to a different one.
    original_body = original_body or []
    predecessor: dict[int, _Statement | None] = {}
    for i, node in enumerate(original_body):
        predecessor[id(node)] = original_body[i - 1] if i > 0 else None

    # Separate imports, docstring, and other fixed nodes
    docstring: list[_Statement] = []
    imports: list[_Statement] = []
    other_fixed: list[_Statement] = []
    main_blocks: list[_Statement] = []

    for i, node in enumerate(fixed_nodes):
        if _is_main_block(node):
            main_blocks.append(node)
        elif _is_import(node):
            imports.append(node)
        elif i == 0 and _is_docstring(node):
            # First statement is module docstring
            docstring.append(node)
        else:
            other_fixed.append(node)

    # Header region: docstring, then imports (their original blank-line grouping is
    # preserved via each node's leading_lines).
    new_body.extend(docstring)
    new_body.extend(imports)

    # Everything else, in order: module-level calls/statements, sorted units, then
    # __main__ blocks. Spacing is applied explicitly based on statement kinds.
    if imports:
        prev_kind: str | None = "import"
        prev_node: _Statement | None = imports[-1]
    elif docstring:
        prev_kind, prev_node = "docstring", docstring[0]
    else:
        prev_kind, prev_node = None, None

    sequence: list[tuple[str, _Statement]] = [("call", node) for node in other_fixed]
    for name in ordered_names:
        sequence.append((_category(unit_map[name].node, name), unit_map[name].node))
    sequence.extend(("main", node) for node in main_blocks)

    for kind, node in sequence:
        # Constants keep their original blank-line separation when they still follow
        # the statement they followed in the source; otherwise spacing is normalised.
        if (
            kind == "const"
            and prev_kind not in (None, "func", "class", "main")
            and prev_node is not None
            and predecessor.get(id(node)) is prev_node
        ):
            new_body.append(node)
        else:
            for _ in range(_blanks_before(prev_kind, kind)):
                new_body.append(cst.EmptyLine())
            new_body.append(_strip_leading(node))
        prev_kind, prev_node = kind, node

    module = cst.Module(body=new_body)
    code = module.code
    if header:
        code = header + "\n\n" + code
    return code


def _category(node: _Statement, name: str) -> str:
    """Classify a statement for spacing purposes.

    Returns:
        One of ``"func"``, ``"class"``, ``"assert"`` or ``"const"``.
    """
    if m.matches(node, m.FunctionDef()):
        return "func"
    if m.matches(node, m.ClassDef()):
        return "class"
    if name.startswith("_assert"):
        return "assert"
    return "const"


def _blanks_before(prev: str | None, cur: str) -> int:
    """Return the number of blank lines to insert before ``cur`` given ``prev``.

    Rules:
    - Nothing precedes the first statement.
    - Functions, classes and ``__main__`` blocks get two blank lines.
    - Asserts stick to the statement they follow.
    - A constant or module-level call gets two blank lines after a function/class,
      no blank line after another constant (constants are grouped), and one blank
      line after imports/docstring/another call.

    Returns:
        Number of blank lines (0, 1 or 2).
    """
    if prev is None:
        return 0
    if cur in ("func", "class", "main"):
        return 2
    if cur == "assert":
        return 0
    if prev in ("func", "class", "main"):
        return 2
    if prev == "const":
        return 0
    return 1


def _strip_leading(node: _Statement) -> _Statement:
    """Strip leading blank lines from a statement, preserving comment lines.

    Returns:
        The statement with blank leading lines removed.
    """
    if isinstance(node, cst.SimpleStatementLine):
        return node.with_changes(
            leading_lines=tuple(ll for ll in node.leading_lines if ll.comment)
        )
    return node.with_changes(leading_lines=())


def rewrite_class_body(
    units: list[SortableUnit], fixed_nodes: list[t.Any], ordered_names: list[str]
) -> list[t.Any]:
    """Rewrite a class body with methods in the specified order.

    Args:
        units: All sortable methods.
        fixed_nodes: Non-sortable nodes to keep in place.
        ordered_names: Method names in desired order.

    Returns:
        New class body as list of statements.
    """
    unit_map = {unit.name: unit for unit in units}
    new_body: list[t.Any] = []

    # Add fixed nodes first
    new_body.extend(fixed_nodes)

    # Add sorted methods
    for name in ordered_names:
        unit = unit_map[name]
        if m.matches(unit.node, m.FunctionDef()):
            new_body.append(unit.node)

    return new_body


def _is_main_block(node: cst.CSTNode) -> bool:
    """Check if a node is an `if __name__ == "__main__":` block.

    Returns:
        True if the node is a main guard block.
    """
    if not m.matches(node, m.If()):
        return False
    assert isinstance(node, cst.If)
    test = node.test
    if not m.matches(test, m.Comparison()):
        return False
    assert isinstance(test, cst.Comparison)
    if len(test.comparisons) != 1:
        return False
    if not m.matches(test.left, m.Name(value="__name__")):
        return False
    comp = test.comparisons[0]
    if not m.matches(comp.operator, m.Equal()):
        return False
    is_main = m.matches(
        comp.comparator, m.SimpleString(value="'__main__'")
    ) or m.matches(comp.comparator, m.SimpleString(value='"__main__"'))
    return is_main


def _is_import(node: cst.CSTNode) -> bool:
    """Check if a node is an import statement.

    Returns:
        True if the node is an import (Import or ImportFrom).
    """
    # Imports are wrapped in SimpleStatementLine
    if not m.matches(node, m.SimpleStatementLine()):
        return False
    assert isinstance(node, cst.SimpleStatementLine)
    if len(node.body) != 1:
        return False
    stmt = node.body[0]
    return m.matches(stmt, m.Import()) or m.matches(stmt, m.ImportFrom())


def _is_docstring(node: cst.CSTNode) -> bool:
    """Check if a node is a module docstring (expression statement with just a string).

    Returns:
        True if the node is a simple string expression (docstring).
    """
    if not m.matches(node, m.SimpleStatementLine()):
        return False
    assert isinstance(node, cst.SimpleStatementLine)
    if len(node.body) != 1:
        return False
    expr = node.body[0]
    return m.matches(expr, m.Expr()) and isinstance(expr, cst.Expr) and m.matches(expr.value, m.SimpleString())
