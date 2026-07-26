"""Reassemble sorted units back into source code."""

import typing as t

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit, _Statement


def rewrite_module(
    units: list[SortableUnit],
    fixed_nodes: list[_Statement],
    ordered_names: list[str],
    header: str = "",
) -> str:
    """Rewrite a module with functions in the specified order.

    Args:
        units: All sortable units.
        fixed_nodes: Non-sortable nodes to keep in place.
        ordered_names: Unit names in desired order.
        header: Module header to preserve (e.g., uv script metadata).

    Returns:
        Reformatted source code.
    """
    unit_map = {unit.name: unit for unit in units}
    new_body: list[_Statement] = []

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

    # Order: docstring, imports, comments, sorted units, __main__ blocks
    new_body.extend(docstring)
    new_body.extend(imports)
    new_body.extend(other_fixed)  # Preserves standalone comments

    # Add blank line after imports/comments before sorted units
    if ordered_names:
        new_body.append(cst.EmptyLine())

    # Add all sorted units in dependency order, with spacing
    # Strip leading empty lines from all nodes since we control spacing
    prev_was_constant = False
    for i, name in enumerate(ordered_names):
        unit = unit_map[name]
        is_constant = isinstance(unit.node, (cst.Assign, cst.AnnAssign))

        # Add blank line between constants and functions
        if i > 0 and prev_was_constant != is_constant:
            if is_constant or i > 0:  # Always add between different types
                new_body.append(cst.EmptyLine())

        if is_constant:
            # Wrap assignment in SimpleStatementLine
            new_body.append(cst.SimpleStatementLine(body=[unit.node]))
        elif m.matches(unit.node, m.FunctionDef()):
            assert isinstance(unit.node, cst.FunctionDef)
            func = unit.node.with_changes(leading_lines=())
            new_body.append(func)
        elif m.matches(unit.node, m.ClassDef()):
            assert isinstance(unit.node, cst.ClassDef)
            cls = unit.node.with_changes(leading_lines=())
            new_body.append(cls)

        prev_was_constant = is_constant

    # Finally __main__ blocks
    new_body.extend(main_blocks)

    module = cst.Module(body=new_body)
    code = module.code
    if header:
        code = header + "\n\n" + code
    return code


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
