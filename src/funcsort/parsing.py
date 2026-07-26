"""Parsing Python modules and classes into sortable units."""

import typing as t

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit, _Statement


def parse_module(source: str) -> tuple[list[SortableUnit], list[_Statement]]:
    """Parse a Python module into sortable units and fixed nodes.

    Sortable units include functions, classes, and constants (assignments).

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
        elif m.matches(statement, m.ClassDef()):
            class_def = statement
            assert isinstance(class_def, cst.ClassDef)
            units.append(
                SortableUnit(name=class_def.name.value, node=class_def, is_entry=False)
            )
        elif m.matches(statement, m.SimpleStatementLine()):
            assert isinstance(statement, cst.SimpleStatementLine)
            # Check for annotated assignments and regular assignments
            for inner_stmt in statement.body:
                if m.matches(inner_stmt, m.AnnAssign()):
                    assert isinstance(inner_stmt, cst.AnnAssign)
                    if inner_stmt.target and m.matches(inner_stmt.target, m.Name()):
                        assert isinstance(inner_stmt.target, cst.Name)
                        units.append(
                            SortableUnit(
                                name=inner_stmt.target.value,
                                node=inner_stmt,
                                is_entry=False,
                            )
                        )
                        break
                elif m.matches(inner_stmt, m.Assign()):
                    assert isinstance(inner_stmt, cst.Assign)
                    # Handle single-target assignments
                    if len(inner_stmt.targets) == 1 and m.matches(
                        inner_stmt.targets[0].target, m.Name()
                    ):
                        assert isinstance(inner_stmt.targets[0].target, cst.Name)
                        units.append(
                            SortableUnit(
                                name=inner_stmt.targets[0].target.value,
                                node=inner_stmt,
                                is_entry=False,
                            )
                        )
                        break
            else:
                # No assignment found in this statement, treat as fixed
                fixed_nodes.append(statement)
        else:
            fixed_nodes.append(statement)

    return units, fixed_nodes


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
