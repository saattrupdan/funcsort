"""Reassemble a run of definitions with normalised PEP 8 spacing."""

import libcst as cst

# A "definition" is the only thing funcsort reorders. Both node types carry the
# ``name`` and ``leading_lines`` attributes the reordering relies on.
Definition = cst.FunctionDef | cst.ClassDef


def rebuild_run(
    run: list[Definition],
    order: list[int],
    blank_count: int,
    preserve_first_leading: bool,
) -> list[Definition]:
    """Return the definitions of ``run`` in ``order`` with normalised spacing.

    Each definition after the first is separated by ``blank_count`` blank lines,
    with its own leading comments preserved. The first definition keeps its
    original leading when the run starts the body (``preserve_first_leading``);
    otherwise it too gets ``blank_count`` blank lines so a function/class is
    properly separated from the preceding code.

    Args:
        run: The consecutive definition nodes, in original order.
        order: A permutation of ``range(len(run))`` giving the new order.
        blank_count: Blank lines before each definition (2 at module level, 1
            inside a class).
        preserve_first_leading: Whether the run is the first thing in its body, in
            which case the leading lines of the first definition are kept as-is.

    Returns:
        The reordered nodes with adjusted leading lines.
    """
    result: list[Definition] = []
    for position, idx in enumerate(order):
        node = run[idx]
        comments = tuple(ll for ll in node.leading_lines if ll.comment)
        if position == 0 and preserve_first_leading:
            leading = comments
        else:
            blanks = tuple(cst.EmptyLine(indent=False) for _ in range(blank_count))
            leading = blanks + comments
        result.append(node.with_changes(leading_lines=leading))
    return result
