"""Test comment preservation on constants."""

from funcsort.core import sort_source


class TestCommentPreservation:
    """Tests for preserving comments on constants and other units."""

    def test_asserts_after_constants(self) -> None:
        """Assert statements referencing constants - constants stay in original order.

        Note: if assert comes before constant (runtime error), funcsort doesn't fix it
        because constants are not moved.
        """
        code = """
TRAIN_SIZE = 1024

assert TRAIN_SIZE % 2 == 0
"""
        result = sort_source(code)
        train_idx = result.index("TRAIN_SIZE =")
        assert_idx = result.index("assert")
        assert train_idx < assert_idx, "Constant should be before assert"

    def test_blank_lines_between_constant_blocks_preserved(self) -> None:
        """Blank-line separation between constant blocks is kept, not collapsed.

        When constants stay in their original order, the blank lines separating
        logical blocks (and their leading comments) must be preserved rather than
        packed together with no separation.

        Raises:
            AssertionError:
                If the question-answering block comment is not found.
        """
        code = '''"""Constants used in the dataset creation scripts."""

# Bounds on the size of texts in sequence classification datasets
MIN_NUM_CHARS_IN_DOCUMENT = 2
MAX_NUM_CHARS_IN_DOCUMENT = 5000


# Bounds on the size of texts in question answering datasets
MIN_NUM_CHARS_IN_CONTEXT = 30
MAX_NUM_CHARS_IN_CONTEXT = 5000


# Bounds on the size of texts in summarisation datasets
MIN_NUM_CHARS_IN_ARTICLE = 30
MAX_NUM_CHARS_IN_ARTICLE = 6000
'''
        result = sort_source(code)

        # Nothing was reordered, so the output should be unchanged.
        assert result == code

        # Explicitly: two blank lines separate each block, and comments survive.
        lines = result.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# Bounds on the size of texts in question"):
                assert lines[i - 1] == ""
                assert lines[i - 2] == ""
                assert lines[i - 3] == "MAX_NUM_CHARS_IN_DOCUMENT = 5000"
                break
        else:
            raise AssertionError("question-answering block comment not found")

    def test_comment_between_import_and_constant(self) -> None:
        """Comments between imports and constants are preserved."""
        code = """
import os

# This is a comment about the constant
TRAIN_SIZE = 1024
"""
        result = sort_source(code)
        assert "# This is a comment about the constant" in result
        assert "TRAIN_SIZE = 1024" in result

    def test_comment_on_constant_in_middle_of_module(self) -> None:
        """Comments on constants in the middle of a module are preserved."""
        code = """
FIRST = 1

# Comment about second constant
SECOND = 2
"""
        result = sort_source(code)
        assert "# Comment about second constant" in result
        assert "SECOND = 2" in result
        # Comment should appear right before SECOND
        comment_idx = result.index("# Comment about second constant")
        second_idx = result.index("SECOND = 2")
        assert comment_idx < second_idx

    def test_multiple_asserts_same_constant(self) -> None:
        """Multiple asserts on the same constant - constants stay in original order."""
        code = """
TRAIN_SIZE = 1024

assert TRAIN_SIZE > 0
assert TRAIN_SIZE % 2 == 0
"""
        result = sort_source(code)
        train_idx = result.index("TRAIN_SIZE =")
        # Both asserts should come after TRAIN_SIZE
        assert train_idx < result.index("assert TRAIN_SIZE > 0")
        assert train_idx < result.index("assert TRAIN_SIZE % 2 == 0")
