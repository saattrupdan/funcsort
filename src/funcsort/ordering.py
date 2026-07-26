"""Topological ordering of functions by call hierarchy."""

from collections.abc import Iterable


def order_by_call_hierarchy(
    unit_names: Iterable[str],
    edges: dict[str, set[str]],
    entry_name: str | None = None,
    function_names: set[str] | None = None,
) -> list[str]:
    """Order function names by call hierarchy.

    Entry points (if provided) come first among functions (but after constants).
    Remaining units are ordered so dependencies come before dependents.
    Ties and cycles are broken alphabetically.

    Args:
        unit_names: All unit names to order.
        edges: Dict mapping unit name to set of units it depends on.
        entry_name: Optional entry point name (main or __init__).
        function_names: Set of function/class names (entry point prioritisation applies only among these).

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

    # Move entry point to front among functions only (constants stay at front)
    # Entry point can depend on constants but should come before other functions
    # that it doesn't depend on
    if entry and entry in result and function_names:
        # Find FUNCTION dependencies only
        entry_deps = edges.get(entry, set()) & function_names
        
        if not entry_deps:
            # Entry has no function dependencies - move it to front among functions
            # Find first function in result (that's not a constant)
            first_func_idx = None
            for i, item in enumerate(result):
                if item in function_names:
                    first_func_idx = i
                    break
            
            # Only move if entry is not already the first function
            if first_func_idx is not None and result[first_func_idx] != entry:
                result.remove(entry)
                result.insert(first_func_idx, entry)

    return result
