"""Order a run of function/class definitions by call hierarchy, safely.

The ordering works on indices (not names) so that definitions sharing a name -
for example a property and its setter - are handled correctly.
"""


def order_run(
    names: list[str],
    hard: list[set[int]],
    soft: list[set[int]],
    entry_name: str | None = None,
) -> list[int]:
    """Return a safe ordering of a run of definitions.

    Definition-time dependencies (``hard``) are strict: a definition never appears
    before something it needs at definition time. Within that constraint, the call
    hierarchy (``soft``) is used as a preference - callers before callees, with the
    entry point first - and ties break alphabetically then by original position.

    Args:
        names: Definition names, in original order.
        hard: ``hard[i]`` is the set of indices that must precede ``i``.
        soft: ``soft[i]`` is the set of indices ``i`` calls (callees).
        entry_name: Optional entry point name (``main`` or ``__init__``).

    Returns:
        A permutation of ``range(len(names))``.
    """
    n = len(names)
    if n <= 1:
        return list(range(n))

    preferred = _preferred_order(names, soft, entry_name)

    # Stable topological sort: walk the preferred order, emitting the first index
    # whose hard dependencies are all satisfied. On a cycle, fall back to the next
    # preferred index so the original relative order is kept.
    emitted = [False] * n
    result: list[int] = []
    remaining = list(preferred)
    while remaining:
        pick = next(
            (idx for idx in remaining if all(emitted[d] for d in hard[idx])),
            remaining[0],
        )
        emitted[pick] = True
        result.append(pick)
        remaining.remove(pick)
    return result


def _preferred_order(
    names: list[str], soft: list[set[int]], entry_name: str | None
) -> list[int]:
    """Compute the call-hierarchy preference order (ignoring hard constraints).

    Callers appear before callees (top-down call order).

    Args:
        names: Definition names, in original order.
        soft: ``soft[i]`` is the set of indices ``i`` calls (callees).
        entry_name: Optional entry point name.

    Returns:
        A permutation of ``range(len(names))``.
    """
    n = len(names)
    emitted = [False] * n
    order: list[int] = []

    def key(i: int) -> tuple[str, int]:
        return (names[i], i)

    def emit_preorder(i: int, path: set[int]) -> None:
        if emitted[i] or i in path:
            return
        path.add(i)
        emitted[i] = True
        order.append(i)
        for dep in sorted(soft[i], key=key):
            emit_preorder(dep, path)
        path.discard(i)

    entry_idx = next((i for i in range(n) if names[i] == entry_name), None)
    if entry_idx is not None:
        emit_preorder(entry_idx, set())

    roots, _ = _build_call_tree(names, soft)
    for i in roots:
        emit_preorder(i, set())

    for i in sorted(range(n), key=key):
        if not emitted[i]:
            emit_preorder(i, set())

    return order


def _build_call_tree(
    names: list[str], soft: list[set[int]]
) -> tuple[list[int], list[bool]]:
    """Find root functions (not called by anyone) in alphabetical order.

    Args:
        names: Definition names.
        soft: ``soft[i]`` is the set of indices ``i`` calls (callees).

    Returns:
        Tuple of (root indices in alphabetical order, is_callee flags).
    """
    n = len(names)
    is_callee = [False] * n
    for i in range(n):
        for j in soft[i]:
            is_callee[j] = True

    def key(i: int) -> tuple[str, int]:
        return (names[i], i)

    roots = [i for i in range(n) if not is_callee[i]]
    return sorted(roots, key=key), is_callee
