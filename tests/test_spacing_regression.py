"""Regression tests for spacing issues."""

from funcsort.core import sort_source


class TestSpacingRegression:
    """Regression tests for PEP 8 spacing issues."""

    def test_allocine_regression_imports_comment_function(self) -> None:
        """Regression: Allocine script - imports, comment, then function (2 blanks).

        Bug: The newline before `main()` was removed when the file was processed.
        The file has imports, a comment line, then `def main()` - should preserve
        the 2 blank lines before the function.
        """
        code = """
import pandas as pd

# These constants are used only inside pandas .query() strings, so the linter
# cannot see the use.
from constants import MAX_NUM_CHARS_IN_DOCUMENT  # noqa: F401
from huggingface_hub import HfApi


def main() -> None:
    repo_id = "tblard/allocine"
    dataset = load_dataset(path=repo_id, token=True)
"""
        result = sort_source(code)
        lines = result.split("\n")
        # Find the function
        for i, line in enumerate(lines):
            if line.strip().startswith("def main"):
                # Should have 2 blank lines before it
                assert lines[i - 1] == "", (
                    f"no blank line before main at {i}, got {lines[i - 1]!r}"
                )
                assert lines[i - 2] == "", (
                    f"need 2 blank lines before main at {i}, got {lines[i - 2]!r}"
                )
                # Line before blanks should be the last import (not blank)
                assert "HfApi" in lines[i - 3] or "import" in lines[i - 3], (
                    f"no import before blanks at {i - 3}, got {lines[i - 3]!r}"
                )
                break

    def test_constants_then_function_two_blank_lines(self) -> None:
        """Regression: constants followed by function should have 2 blank lines."""
        code = """
TRAIN_SIZE = 1024


def main() -> None:
    pass
"""
        result = sort_source(code)
        lines = result.split("\n")
        # Find first function after constants
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                # Should have 2 blank lines before it
                assert lines[i - 1] == "", (
                    f"no blank line before func at {i}, got {lines[i - 1]!r}"
                )
                assert lines[i - 2] == "", (
                    f"need 2 blank lines before func at {i}, got {lines[i - 2]!r}"
                )
                break

    def test_function_to_function_two_blank_lines(self) -> None:
        """Regression: functions should be separated by 2 blank lines."""
        code = """
def helper():
    pass


def main():
    pass
"""
        result = sort_source(code)
        lines = result.split("\n")
        # Count functions and check spacing
        func_indices = [
            i for i, line in enumerate(lines) if line.strip().startswith("def ")
        ]
        for i in func_indices[1:]:  # Skip first function
            assert lines[i - 1] == "", (
                f"Expected blank line before function at line {i}"
            )
            assert lines[i - 2] == "", (
                f"Expected two blank lines before function at line {i}"
            )

    def test_imports_then_function_two_blank_lines(self) -> None:
        """Regression: imports followed by function should have 2 blank lines (PEP 8).

        Bug: Previously only 1 blank line was inserted before the first function.
        PEP 8 requires 2 blank lines before top-level function definitions.
        """
        code = """
import pandas as pd

def main() -> None:
    pass


if __name__ == "__main__":
    main()
"""
        result = sort_source(code)
        lines = result.split("\n")
        # Find first function after imports
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                # Should have 2 blank lines before it
                assert lines[i - 1] == "", (
                    f"no blank line before func at {i}, got {lines[i - 1]!r}"
                )
                assert lines[i - 2] == "", (
                    f"need 2 blank lines before func at {i}, got {lines[i - 2]!r}"
                )
                # Line before blanks should be import or other code (not blank)
                assert lines[i - 3].strip(), (
                    f"no code before blanks at {i - 3}, got {lines[i - 3]!r}"
                )
                break
