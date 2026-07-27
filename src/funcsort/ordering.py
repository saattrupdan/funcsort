"""Order a run of function/class definitions by call hierarchy, safely.

The ordering works on indices (not names) so that definitions sharing a name -
for example a property and its setter - are handled correctly.
"""


def _preferred_order(
    names: list[str], soft: list[set[int]], entry_name: str | None
) -> list[int]:
    """Compute the call-hierarchy preference order (ignoring hard constraints).

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

    def emit_postorder(i: int, path: set[int]) -> None:
        if emitted[i] or i in path:
            return
        path.add(i)
        for dep in sorted(soft[i], key=key):
            emit_postorder(dep, path)
        path.discard(i)
        emitted[i] = True
        order.append(i)

    entry_idx = next((i for i in range(n) if names[i] == entry_name), None)
    if entry_idx is not None:
        # Entry point first, then the functions it calls, top-down.
        emit_preorder(entry_idx, set())

    # Remaining definitions: callees before callers.
    for i in sorted(range(n), key=key):
        emit_postorder(i, set())

    return order


def order_run(
    names: list[str],
    hard: list[set[int]],
    soft: list[set[int]],
    entry_name: str | None = None,
) -> list[int]:
    """Return a safe ordering of a run of definitions.

    Definition-time dependencies (``hard``) are strict: a definition never appears
    before something it needs at definition time. Within that constraint, the call
    hierarchy (``soft``) is used as a preference - callees before callers, with the
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
