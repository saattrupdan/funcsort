"""Parsing Python modules and classes into sortable units."""

import typing as t

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit, _Statement


def parse_class_body(class_def: cst.ClassDef) -> tuple[list[SortableUnit], list[t.Any]]:
    """Parse a class body into sortable methods and fixed nodes.

    Args:
        class_def: The class definition node.

    Returns:
        Tuple of (sortable methods, fixed nodes in original order).
    """
    units: list[SortableUnit] = []
    fixed_nodes: list[t.Any] = []

    for statement in class_def.body.body:
        if m.matches(statement, m.FunctionDef()):
            func_def = statement
            assert isinstance(func_def, cst.FunctionDef)
            is_entry = func_def.name.value == "__init__"
            units.append(
                SortableUnit(name=func_def.name.value, node=func_def, is_entry=is_entry)
            )
        else:
            fixed_nodes.append(statement)

    return units, fixed_nodes


def parse_module(source: str) -> tuple[list[SortableUnit], list[_Statement]]:
    """Parse a Python module into sortable functions and fixed nodes.

    Args:
        source: Python source code.

    Returns:
        Tuple of (sortable units, fixed nodes in original order).
    """
    module = cst.parse_module(source)

    units: list[SortableUnit] = []
    fixed_nodes: list[_Statement] = []

    for statement in module.body:
        if m.matches(statement, m.FunctionDef()):
            func_def = statement
            assert isinstance(func_def, cst.FunctionDef)
            is_entry = func_def.name.value == "main"
            units.append(
                SortableUnit(name=func_def.name.value, node=func_def, is_entry=is_entry)
            )
        else:
            fixed_nodes.append(statement)

    return units, fixed_nodes
