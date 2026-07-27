"""Core sorting logic for Python modules.

funcsort only reorders top-level functions/classes and methods within classes,
and only within *runs* of consecutive definitions. Constants, imports and any
other module-level code are anchors that never move. Reordering is constrained so
it can never break definition-time name resolution (decorators, base classes,
annotations, class-body defaults, property/setter pairings).
"""

from collections.abc import Sequence
from pathlib import Path

import libcst as cst
import pathspec

from .call_graph import call_refs, def_time_refs
from .ordering import order_run
from .rewrite import Definition, rebuild_run


def _sort_run(
    run: list[Definition], entry_name: str, blank_count: int, at_start: bool
) -> list[Definition]:
    """Sort a single run of consecutive function/class definitions.

    Args:
        run: Consecutive definition nodes.
        entry_name: Entry point name to prioritise.
        blank_count: Blank lines between definitions.
        at_start: Whether this run is the first thing in its body.

    Returns:
        The (possibly reordered) definition nodes, with normalised spacing.
    """
    if len(run) <= 1:
        order = [0] if run else []
    else:
        names = [node.name.value for node in run]
        members = set(names)
        name_to_indices: dict[str, list[int]] = {}
        for idx, name in enumerate(names):
            name_to_indices.setdefault(name, []).append(idx)

        hard: list[set[int]] = [set() for _ in run]
        soft: list[set[int]] = [set() for _ in run]
        for idx, node in enumerate(run):
            for name in def_time_refs(node) & members:
                hard[idx].update(j for j in name_to_indices[name] if j != idx)
            for name in call_refs(node) & members:
                soft[idx].update(j for j in name_to_indices[name] if j != idx)

        # Keep definitions that share a name (e.g. a property and its setter) in
        # their original relative order.
        for indices in name_to_indices.values():
            for earlier, later in zip(indices, indices[1:]):
                hard[later].add(earlier)

        order = order_run(names, hard, soft, entry_name)

    return rebuild_run(run, order, blank_count, preserve_first_leading=at_start)


def _reorder(
    nodes: Sequence[cst.BaseStatement], entry_name: str, blank_count: int
) -> list[cst.BaseStatement]:
    """Reorder each run of consecutive definitions, keeping anchors in place.

    Args:
        nodes: The statements of a module or class body, in order.
        entry_name: Entry point name to prioritise within a run.
        blank_count: Blank lines between definitions when a run is reordered.

    Returns:
        The statements with each definition-run sorted; non-definitions untouched.
    """
    result: list[cst.BaseStatement] = []
    i = 0
    while i < len(nodes):
        start = i
        run: list[Definition] = []
        while i < len(nodes) and isinstance(
            node := nodes[i], (cst.FunctionDef, cst.ClassDef)
        ):
            run.append(node)
            i += 1
        if run:
            result.extend(_sort_run(run, entry_name, blank_count, at_start=start == 0))
        else:
            result.append(nodes[i])
            i += 1
    return result


def _same_sequence(a: Sequence[cst.CSTNode], b: Sequence[cst.CSTNode]) -> bool:
    """Return whether two node lists are the identical objects in the same order."""
    return len(a) == len(b) and all(x is y for x, y in zip(a, b))


class _ClassTransformer(cst.CSTTransformer):
    """Sort methods within each class body, leaving other statements in place."""

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Reorder methods in the class body if it is an indented block.

        Returns:
            The class with its methods sorted, or unchanged if nothing moved.
        """
        block = updated_node.body
        if not isinstance(block, cst.IndentedBlock):
            return updated_node

        old_body = list(block.body)
        new_body = _reorder(old_body, entry_name="__init__", blank_count=1)
        if _same_sequence(old_body, new_body):
            return updated_node
        return updated_node.with_changes(body=block.with_changes(body=tuple(new_body)))


def _is_ignored(file_path: Path, start_dir: Path) -> bool:
    """Check if a file is ignored by gitignore patterns in parent directories.

    Walks from the file's directory up to the filesystem root, checking each
    directory's .gitignore file. Patterns are matched relative to where the
    .gitignore is located.

    Args:
        file_path: File to check.
        start_dir: Directory where search started.

    Returns:
        True if file is ignored by any .gitignore in parent directories.
    """
    # Use absolute paths to ensure proper parent traversal
    file_path = file_path.resolve()
    start_dir = start_dir.resolve()

    # Walk from file's directory up to filesystem root
    current = file_path.parent
    while current != current.parent:
        gitignore = current / ".gitignore"
        if gitignore.exists():
            patterns = gitignore.read_text(encoding="utf-8").splitlines()
            spec = pathspec.GitIgnoreSpec.from_lines(patterns)
            try:
                rel_path = file_path.relative_to(current).as_posix()
                if spec.match_file(rel_path):
                    return True
            except ValueError:
                # file_path is not relative to current, skip this .gitignore
                pass
        current = current.parent

    return False


def sort_source(source: str) -> str:
    """Sort functions, classes and methods in Python source code.

    Args:
        source: Python source code.

    Returns:
        Source with definitions sorted by call hierarchy. Anything that is not a
        top-level function/class (or method) keeps its original position.
    """
    # Extract module header (e.g., uv script metadata: # /// script ... # ///).
    # Split on "\n" (not splitlines) so a trailing newline survives the round-trip.
    header = ""
    lines = source.split("\n")
    if lines and lines[0].startswith("# ///"):
        header_lines = []
        i = 0
        while i < len(lines):
            header_lines.append(lines[i])
            if lines[i].strip() == "# ///":
                break
            i += 1
        header = "\n".join(header_lines)
        # Skip header and any blank lines after it
        while i + 1 < len(lines) and lines[i + 1] == "":
            i += 1
        source = "\n".join(lines[i + 1 :])

    module = cst.parse_module(source)

    # Sort top-level functions/classes, then methods within each class.
    new_body = _reorder(list(module.body), entry_name="main", blank_count=2)
    module = module.with_changes(body=tuple(new_body))
    module = module.visit(_ClassTransformer())

    code = module.code
    if header:
        code = header + "\n\n" + code
    return code


def process_path(path: Path, fix: bool) -> tuple[bool, list[Path]]:
    """Process a file or directory.

    Args:
        path: File or directory to process.
        fix: Whether to fix in place or just check.

    Returns:
        Tuple of (should_exit_nonzero, list of processed files).
    """
    if path.is_file():
        files = [path]
    elif path.is_dir():
        all_files = list(path.rglob("*.py"))
        files = [f for f in all_files if not _is_ignored(f, path)]
    else:
        return False, []

    changed_files: list[Path] = []
    should_exit = False

    for file_path in files:
        source = file_path.read_text(encoding="utf-8")
        sorted_source = sort_source(source)

        if sorted_source != source:
            changed_files.append(file_path)
            should_exit = True
            if fix:
                file_path.write_text(sorted_source, encoding="utf-8")

    return should_exit, changed_files
