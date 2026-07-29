"""Fast, read-only traversal of libcst nodes.

libcst's own ``CSTNode.visit`` and ``CSTNode.children`` rebuild (or re-derive)
their results on every call - work funcsort does not need when it only wants to
read names or find nested classes. These helpers walk the concrete dataclass
fields directly instead, which is several times cheaper on large modules.
"""

from collections.abc import Iterator
from dataclasses import fields as dataclass_fields

import libcst as cst

_FIELD_NAMES: dict[type[cst.CSTNode], tuple[str, ...]] = {}


def walk(node: cst.CSTNode) -> Iterator[cst.CSTNode]:
    """Yield ``node`` and every descendant node.

    This reads child nodes straight from the dataclass fields, avoiding the
    node reconstruction that ``CSTNode.visit`` performs. Order is unspecified,
    which is fine for the set-based inspection funcsort uses it for.

    Args:
        node: The root node.

    Yields:
        ``node`` followed by all of its descendant nodes.
    """
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        for name in field_names(current):
            value = getattr(current, name)
            if isinstance(value, cst.CSTNode):
                stack.append(value)
            elif type(value) is tuple:
                stack.extend(item for item in value if isinstance(item, cst.CSTNode))


def field_names(node: cst.CSTNode) -> tuple[str, ...]:
    """Return the dataclass field names of a node's type, cached by type.

    Args:
        node: The node whose field names are needed.

    Returns:
        The field names, in declaration order.
    """
    node_type = type(node)
    names = _FIELD_NAMES.get(node_type)
    if names is None:
        names = tuple(field.name for field in dataclass_fields(node))
        _FIELD_NAMES[node_type] = names
    return names
