"""Topological ordering of functions by call hierarchy."""

from collections.abc import Iterable


def order_by_call_hierarchy(
    unit_names: Iterable[str], edges: dict[str, set[str]], entry_name: str | None = None
) -> list[str]:
    """Order function names by call hierarchy.

    Entry point (if provided) comes first. Remaining functions are ordered
    so callers appear before callees. Ties and cycles are broken alphabetically.

    Args:
        unit_names: All function names to order.
        edges: Dict mapping function name to set of functions it calls.
        entry_name: Optional entry point name (main or __init__).

    Returns:
        Ordered list of function names.
    """
    names = list(unit_names)
    names.sort()  # Start alphabetically for determinism

    if not names:
        return []

    # Keep entry in the graph but mark it for special handling
    entry: str | None = None
    if entry_name and entry_name in names:
        entry = entry_name

    # DFS-based: for each node, visit its DEPENDENCIES first (callees), then add the node
    # This gives "definitions before usages" order
    visited: set[str] = set()
    path: set[str] = set()
    result: list[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in path:
            # Cycle detected - skip (will be handled by alphabetical tie-breaking elsewhere)
            return
        path.add(name)
        # Visit dependencies first (sorted for determinism)
        for dep in sorted(edges.get(name, set())):
            if dep in names:
                visit(dep)
        path.remove(name)
        visited.add(name)
        result.append(name)

    for name in sorted(names):
        if name not in visited:
            visit(name)

    # Move entry point to front if present
    if entry and entry in result:
        result.remove(entry)
        result.insert(0, entry)

    return result
