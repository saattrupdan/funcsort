"""Order a run of function/class definitions by call hierarchy, safely."""


def _key(names: list[str], idx: int) -> tuple[str, int]:
    """Return a stable alphabetical key."""
    return names[idx], idx


def order_run(
    names: list[str],
    hard: list[set[int]],
    soft: list[set[int]],
    entry_name: str | None = None,
) -> list[int]:
    """Return a safe, level-based caller-before-callee ordering.

    Definition-time dependencies are strict. Call-time dependencies determine
    breadth-first levels; members of a recursive component are alphabetical.

    Args:
        names: Definition names, in original order.
        hard: ``hard[i]`` contains definitions required before ``i``.
        soft: ``soft[i]`` contains definitions called by ``i``.
        entry_name: Optional entry point name (``main`` or ``__init__``).

    Returns:
        A permutation of the definition indices.
    """
    n = len(names)
    if n <= 1:
        return list(range(n))

    components = _components(soft)
    component_of = [0] * n
    for component_idx, component in enumerate(components):
        for node in component:
            component_of[node] = component_idx

    # Condense recursive call groups, then order the resulting DAG by depth.
    callers: list[set[int]] = [set() for _ in components]
    for caller, callees in enumerate(soft):
        for callee in callees:
            source = component_of[caller]
            target = component_of[callee]
            if source != target:
                callers[target].add(source)

    level = [0] * len(components)
    remaining = set(range(len(components)))
    while remaining:
        ready = [idx for idx in remaining if not (callers[idx] & remaining)]
        ready.sort(key=lambda idx: min(_key(names, node) for node in components[idx]))
        for idx in ready:
            level[idx] = max((level[parent] + 1 for parent in callers[idx]), default=0)
        remaining.difference_update(ready)

    ranks = [level[component_of[idx]] for idx in range(n)]
    entry_idx = next((i for i, name in enumerate(names) if name == entry_name), None)
    if entry_idx is not None:
        ranks[entry_idx] = -1

    preferred = sorted(range(n), key=lambda idx: (ranks[idx], *_key(names, idx)))
    return _respect_hard_dependencies(preferred=preferred, hard=hard)


def _components(graph: list[set[int]]) -> list[list[int]]:
    """Return strongly connected components of a directed graph."""
    index = 0
    indices = [-1] * len(graph)
    lowlinks = [0] * len(graph)
    stack: list[int] = []
    on_stack: set[int] = set()
    components: list[list[int]] = []

    def visit(node: int) -> None:
        nonlocal index
        indices[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for neighbour in graph[node]:
            if indices[neighbour] == -1:
                visit(neighbour)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbour])
            elif neighbour in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbour])
        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(component)

    for node in range(len(graph)):
        if indices[node] == -1:
            visit(node)
    return components


def _respect_hard_dependencies(preferred: list[int], hard: list[set[int]]) -> list[int]:
    """Apply strict definition-time constraints to a preferred order.

    Args:
        preferred: Indices in preferred order.
        hard: Definitions that must precede each index.

    Returns:
        A safe permutation of the preferred indices.
    """
    emitted = [False] * len(preferred)
    result: list[int] = []
    remaining = list(preferred)
    while remaining:
        available = next(
            (
                idx
                for idx in remaining
                if all(emitted[dependency] for dependency in hard[idx])
            ),
            remaining[0],
        )
        emitted[available] = True
        result.append(available)
        remaining.remove(available)
    return result
