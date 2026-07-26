"""Data models for sortable units."""

import dataclasses as dc

import libcst as cst

#: Type alias for module body statements
_Statement = cst.SimpleStatementLine | cst.BaseCompoundStatement


@dc.dataclass
class SortableUnit:
    """A sortable function or method with its AST node.

    Attributes:
        name: Function or method name.
        node: The libcst FunctionDef node.
        is_entry: Whether this is an entry point (main or __init__).
    """

    name: str
    node: cst.FunctionDef
    is_entry: bool = False
