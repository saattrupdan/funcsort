"""Data models for sortable units."""

import dataclasses as dc

import libcst as cst

#: Type alias for module body statements
_Statement = cst.SimpleStatementLine | cst.BaseCompoundStatement


@dc.dataclass
class SortableUnit:
    """A sortable unit (function, class, or constant) with its AST node.

    Attributes:
        name: Function, class, or constant name.
        node: The libcst node (FunctionDef, ClassDef, Assign, or AnnAssign).
        is_entry: Whether this is an entry point (main or __init__).
    """

    name: str
    node: cst.FunctionDef | cst.ClassDef | cst.Assign | cst.AnnAssign
    is_entry: bool = False
