"""Core sorting logic for Python modules."""

from pathlib import Path

import libcst as cst
import pathspec

from .call_graph import build_call_graph
from .ordering import order_by_call_hierarchy
from .parsing import parse_class_body, parse_module
from .rewrite import rewrite_class_body, rewrite_module


class _ClassTransformer(cst.CSTTransformer):
    """Transform class definitions by sorting their methods."""

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        units, fixed_nodes = parse_class_body(updated_node)
        if not units:
            return updated_node

        edges = build_call_graph(units)
        # Only prioritise __init__ among methods (not attributes)
        method_names = {u.name for u in units if "FunctionDef" in type(u.node).__name__}
        ordered = order_by_call_hierarchy(
            unit_names=[unit.name for unit in units],
            edges=edges,
            entry_name="__init__",
            function_names=method_names,
        )
        new_body = rewrite_class_body(units, fixed_nodes, ordered)
        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))


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


def sort_source(source: str) -> str:
    """Sort functions and methods in Python source code.

    Args:
        source: Python source code.

    Returns:
        Source with functions/methods sorted by call hierarchy.
    """
    # Extract module header (e.g., uv script metadata: # /// script ... # ///)
    header = ""
    lines = source.splitlines()
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

    units, fixed_nodes = parse_module(source)
    if not units:
        # No top-level functions, but might have classes with methods
        module = cst.parse_module(source)
        transformer = _ClassTransformer()
        new_module = module.visit(transformer)
        result = new_module.code
    else:
        edges = build_call_graph(units)
        # Only prioritise main among functions (not constants)
        function_names = {u.name for u in units if "FunctionDef" in type(u.node).__name__}
        ordered = order_by_call_hierarchy(
            unit_names=[unit.name for unit in units],
            edges=edges,
            entry_name="main",
            function_names=function_names,
        )
        result = rewrite_module(units, fixed_nodes, ordered, header)

    # Also sort methods in classes
    module = cst.parse_module(result)
    transformer = _ClassTransformer()
    new_module = module.visit(transformer)

    return new_module.code


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
