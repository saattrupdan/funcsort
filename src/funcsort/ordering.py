"""Topological ordering of functions by call hierarchy."""

from collections.abc import Iterable


def order_by_call_hierarchy(
    unit_names: Iterable[str], edges: dict[str, set[str]], entry_name: str | None = None
) -> list[str]:
    """Order function names by call hierarchy.

    Entry points (if provided) come first among units with no dependencies.
    Remaining units are ordered so dependencies come before dependents.
    Ties and cycles are broken alphabetically.

    Args:
        unit_names: All unit names to order.
        edges: Dict mapping unit name to set of units it depends on.
        entry_name: Optional entry point name (main or __init__).

    Returns:
        Ordered list of unit names.
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

    # Move entry point to front only if:
    # 1. It has no dependencies
    # 2. The first item in result is also a function (not a constant)
    # This ensures entry points come first among functions, but constants come before all
    if entry and entry in result:
        entry_deps = edges.get(entry, set()) & set(names)
        if not entry_deps:
            # Check if first item is likely a function (heuristic: starts with lowercase or _)
            first = result[0]
            if first != entry and (first.startswith('_') or first[0].islower()):
                result.remove(entry)
                result.insert(0, entry)

    return result
