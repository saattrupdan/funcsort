"""Reassemble sorted units back into source code."""

import typing as t

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit, _Statement


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


def rewrite_module(
    units: list[SortableUnit], fixed_nodes: list[_Statement], ordered_names: list[str]
) -> str:
    """Rewrite a module with functions in the specified order.

    Args:
        units: All sortable units.
        fixed_nodes: Non-sortable nodes to keep in place.
        ordered_names: Function names in desired order.

    Returns:
        Reformatted source code.
    """
    unit_map = {unit.name: unit for unit in units}
    new_body: list[_Statement] = []

    # Separate __name__ == "__main__" blocks from other fixed nodes
    main_blocks: list[_Statement] = []
    other_fixed: list[_Statement] = []

    for node in fixed_nodes:
        if _is_main_block(node):
            main_blocks.append(node)
        else:
            other_fixed.append(node)

    # Add non-main fixed nodes first (imports, constants, classes, etc.)
    new_body.extend(other_fixed)

    # Add sorted functions
    for name in ordered_names:
        unit = unit_map[name]
        if m.matches(unit.node, m.FunctionDef()):
            new_body.append(unit.node)

    # Add __name__ == "__main__" blocks at the end
    new_body.extend(main_blocks)

    module = cst.Module(body=new_body)
    return module.code
