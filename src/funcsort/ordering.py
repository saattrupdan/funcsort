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

    # Separate entry point if present
    entry: str | None = None
    if entry_name and entry_name in names:
        entry = entry_name
        names.remove(entry)

    result: list[str] = []
    remaining = set(names)

    while remaining:
        # Find functions that don't call any remaining functions
        # (i.e., their callees are already in result or they have no callees)
        ready: list[str] = []
        for name in sorted(remaining):
            callees = edges.get(name, set())
            remaining_callees = callees & remaining
            if not remaining_callees:
                ready.append(name)

        if not ready:
            # Cycle detected - take alphabetically first
            ready = [sorted(remaining)[0]]

        result.extend(ready)
        remaining -= set(ready)

    # Prepend entry point
    if entry:
        return [entry] + result
    return result
