"""Topological ordering of functions, classes and constants by call hierarchy."""

from collections.abc import Iterable


def order_by_call_hierarchy(
    unit_names: Iterable[str],
    edges: dict[str, set[str]],
    entry_name: str | None = None,
    function_names: set[str] | None = None,
    class_names: set[str] | None = None,
) -> list[str]:
    """Order units (functions, classes, constants) by call hierarchy.

    Ordering:
    1. Independent constants (no in-module function/class dependency), in original
       source order.
    2. Dependent constants, each preceded by the functions/classes it depends on
       (callees first), in original source order.
    3. Remaining classes, in dependency order (bases/used classes first).
    4. Remaining functions:
       - With an entry point: the entry point first, then a pre-order (caller before
         callee) walk of the functions it calls, so the reader meets the top-level
         function first. Any functions unreachable from the entry point follow in
         dependency order (callees first).
       - Without an entry point: dependency order (callees before callers).

    Ties are broken alphabetically. Classes count as ``function_names`` when they
    appear as dependencies.

    Args:
        unit_names: All unit names, in original source order.
        edges: Dict mapping unit name to the set of unit names it depends on.
        entry_name: Optional entry point name (``main`` or ``__init__``).
        function_names: Names that are functions or classes.
        class_names: Names that are classes (a subset of ``function_names``).

    Returns:
        Ordered list of unit names.
    """
    original = list(unit_names)
    function_names = function_names or set()
    class_names = class_names or set()

    if not original:
        return []

    constants = [n for n in original if n not in function_names]
    classes = [n for n in original if n in class_names]
    funcs = [n for n in original if n in function_names and n not in class_names]

    def func_deps(name: str) -> set[str]:
        """Return the dependencies of ``name`` that are functions or classes."""
        return edges.get(name, set()) & function_names

    independent_constants = [c for c in constants if not func_deps(c)]
    dependent_constants = [c for c in constants if func_deps(c)]

    result: list[str] = []
    emitted: set[str] = set()

    def emit(name: str) -> None:
        if name not in emitted:
            emitted.add(name)
            result.append(name)

    def emit_postorder(name: str, path: set[str]) -> None:
        """Emit ``name`` after its function/class dependencies (callees first)."""
        if name in emitted or name in path:
            return
        path.add(name)
        for dep in sorted(func_deps(name)):
            emit_postorder(dep, path)
        path.discard(name)
        emit(name)

    def emit_preorder(name: str, path: set[str]) -> None:
        """Emit ``name`` before its function/class dependencies (caller first)."""
        if name in emitted or name in path:
            return
        path.add(name)
        emit(name)
        for dep in sorted(func_deps(name)):
            emit_preorder(dep, path)
        path.discard(name)

    # 1. Independent constants, in original order.
    for const in independent_constants:
        emit(const)

    # 2. Dependent constants, each preceded by its callees, in original order.
    for const in dependent_constants:
        for dep in sorted(func_deps(const)):
            emit_postorder(dep, set())
        emit(const)

    # 3. Remaining classes, in dependency order (bases/used classes first).
    for cls in sorted(classes):
        emit_postorder(cls, set())

    # 4. Remaining functions.
    if entry_name and entry_name in funcs:
        emit_preorder(entry_name, set())
    for func in sorted(funcs):
        emit_postorder(func, set())

    return result
