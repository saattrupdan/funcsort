"""Topological ordering of functions by call hierarchy."""

from collections.abc import Iterable


def order_by_call_hierarchy(
    unit_names: Iterable[str],
    edges: dict[str, set[str]],
    entry_name: str | None = None,
    function_names: set[str] | None = None,
) -> list[str]:
    """Order function names by call hierarchy.

    Ordering semantics:
    1. Constants that don't depend on functions come first (in dependency order)
    2. Functions (entry point first, then others in dependency order)
    3. Constants that depend on functions come after functions (in dependency order)

    Note: Entry point comes BEFORE functions it calls, because Python defines all
    functions at module load time. However, constants that depend on functions must
    come after those functions (runtime requirement).

    Args:
        unit_names: All unit names to order.
        edges: Dict mapping unit name to set of units it depends on.
        entry_name: Optional entry point name (main or __init__).
        function_names: Set of function/class names (entry point prioritisation applies
            only among these).

    Returns:
        Ordered list of unit names.
    """
    names = list(unit_names)
    names.sort()  # Start alphabetically for determinism

    if not names:
        return []

    # Separate constants and functions
    constants = [n for n in names if n not in function_names]
    funcs = [n for n in names if n in function_names]

    # Classify constants: those that depend on functions vs those that don't
    independent_constants = []
    dependent_constants = []
    for c in constants:
        deps_on_funcs = edges.get(c, set()) & function_names
        if deps_on_funcs:
            dependent_constants.append(c)
        else:
            independent_constants.append(c)

    # DFS-based topological sort for independent constants
    visited: set[str] = set()
    path: set[str] = set()
    indep_const_result: list[str] = []

    def visit_indep(name: str) -> None:
        if name in visited:
            return
        if name in path:
            return  # Cycle
        path.add(name)
        for dep in sorted(edges.get(name, set()) & set(independent_constants)):
            visit_indep(dep)
        path.remove(name)
        visited.add(name)
        indep_const_result.append(name)

    for name in independent_constants:
        if name not in visited:
            visit_indep(name)

    # Sort functions: entry point first, then others in dependency order
    if entry_name and entry_name in funcs:
        other_funcs = [f for f in funcs if f != entry_name]
        
        visited_func: set[str] = set()
        path_func: set[str] = set()
        func_result: list[str] = []

        def visit_func(name: str) -> None:
            if name in visited_func:
                return
            if name in path_func:
                return  # Cycle
            path_func.add(name)
            for dep in sorted(edges.get(name, set()) & function_names):
                visit_func(dep)
            path_func.remove(name)
            visited_func.add(name)
            func_result.append(name)

        for name in other_funcs:
            if name not in visited_func:
                visit_func(name)
        
        # Entry first among functions
        sorted_funcs = [entry_name] + func_result
    else:
        # No entry point - sort all functions by dependency
        visited_func: set[str] = set()
        path_func: set[str] = set()
        func_result: list[str] = []

        def visit_func(name: str) -> None:
            if name in visited_func:
                return
            if name in path_func:
                return  # Cycle
            path_func.add(name)
            for dep in sorted(edges.get(name, set()) & function_names):
                visit_func(dep)
            path_func.remove(name)
            visited_func.add(name)
            func_result.append(name)

        for name in funcs:
            if name not in visited_func:
                visit_func(name)
        
        sorted_funcs = func_result

    # DFS-based topological sort for dependent constants
    visited_dep: set[str] = set()
    path_dep: set[str] = set()
    dep_const_result: list[str] = []

    def visit_dep(name: str) -> None:
        if name in visited_dep:
            return
        if name in path_dep:
            return  # Cycle
        path_dep.add(name)
        for dep in sorted(edges.get(name, set()) & set(dependent_constants)):
            visit_dep(dep)
        path_dep.remove(name)
        visited_dep.add(name)
        dep_const_result.append(name)

    for name in dependent_constants:
        if name not in visited_dep:
            visit_dep(name)

    # Combine: independent constants, functions, dependent constants
    return indep_const_result + sorted_funcs + dep_const_result
