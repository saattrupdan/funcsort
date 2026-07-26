"""Test comment preservation on constants."""

from funcsort.core import sort_source


class TestCommentPreservation:
    """Tests for preserving comments on constants and other units."""

    def test_comment_between_import_and_constant(self):
        """Comments between imports and constants are preserved."""
        code = '''
import os

# This is a comment about the constant
TRAIN_SIZE = 1024
'''
        result = sort_source(code)
        assert "# This is a comment about the constant" in result
        assert "TRAIN_SIZE = 1024" in result

    def test_comment_on_constant_in_middle_of_module(self):
        """Comments on constants in the middle of a module are preserved."""
        code = '''
FIRST = 1

# Comment about second constant
SECOND = 2
'''
        result = sort_source(code)
        assert "# Comment about second constant" in result
        assert "SECOND = 2" in result
        # Comment should appear right before SECOND
        comment_idx = result.index("# Comment about second constant")
        second_idx = result.index("SECOND = 2")
        assert comment_idx < second_idx

    def test_asserts_after_constants(self):
        """Assert statements appear after the constants they reference."""
        code = '''
assert TRAIN_SIZE % 2 == 0

TRAIN_SIZE = 1024
'''
        result = sort_source(code)
        train_idx = result.index("TRAIN_SIZE =")
        assert_idx = result.index("assert")
        assert train_idx < assert_idx, "Constant should be before assert"

    def test_multiple_asserts_same_constant(self):
        """Multiple asserts on the same constant all appear after it."""
        code = '''
assert TRAIN_SIZE > 0
assert TRAIN_SIZE % 2 == 0

TRAIN_SIZE = 1024
'''
        result = sort_source(code)
        train_idx = result.index("TRAIN_SIZE =")
        # Both asserts should come after TRAIN_SIZE
        assert train_idx < result.index("assert TRAIN_SIZE > 0")
        assert train_idx < result.index("assert TRAIN_SIZE % 2 == 0")
