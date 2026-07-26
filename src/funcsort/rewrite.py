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
    # other_fixed includes standalone comments and module-level statements
    # (like logging.basicConfig()) - need 2 blank lines after imports
    if other_fixed:
        new_body.append(cst.EmptyLine())
        new_body.append(cst.EmptyLine())
        for node in other_fixed:
            # Strip leading lines from module-level statements
            if isinstance(node, cst.SimpleStatementLine):
                node = node.with_changes(leading_lines=())
            new_body.append(node)

    # Add sorted units in dependency order, with proper spacing
    # PEP 8: 2 blank lines before functions/classes, constants grouped together
    # Asserts (names starting with _assert) don't get blank lines before them
    started = False
    prev_is_constant = False
    for i, name in enumerate(ordered_names):
        unit = unit_map[name]
        is_constant = isinstance(unit.node, cst.SimpleStatementLine)
        is_assert = name.startswith('_assert')

        # Determine spacing before this unit
        if not started:
            # First unit: need 2 blank lines after imports/other_fixed
            new_body.append(cst.EmptyLine())
            new_body.append(cst.EmptyLine())
            started = True
            prev_is_constant = is_constant
        elif is_assert:
            # Asserts don't get blank lines - they stick to previous item
            pass
        elif not prev_is_constant:
            # Function after function: 2 blank lines
            new_body.append(cst.EmptyLine())
            new_body.append(cst.EmptyLine())
        elif is_constant and prev_is_constant:
            # Constant after constant: no blank line (keep together)
            pass
        else:
            # Transition from constant to function: 2 blank lines
            new_body.append(cst.EmptyLine())
            new_body.append(cst.EmptyLine())
        
        prev_is_constant = is_constant

        # Add the unit
        if is_constant:
            assert isinstance(unit.node, cst.SimpleStatementLine)
            # Strip leading blank lines but preserve comments
            comment_lines = tuple(
                ll for ll in unit.node.leading_lines if ll.comment
            )
            stmt = unit.node.with_changes(leading_lines=comment_lines)
            new_body.append(stmt)
        elif m.matches(unit.node, m.FunctionDef()):
            assert isinstance(unit.node, cst.FunctionDef)
            func = unit.node.with_changes(leading_lines=())
            new_body.append(func)
        elif m.matches(unit.node, m.ClassDef()):
            assert isinstance(unit.node, cst.ClassDef)
            cls = unit.node.with_changes(leading_lines=())
            new_body.append(cls)

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
