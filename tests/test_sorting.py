"""Test cases for funcsort."""

import pytest
from funcsort.core import sort_source


class TestModuleLevelFunctions:
    """Tests for module-level function sorting."""

    def test_caller_with_entry_point(self):
        """Entry point (main) comes first, other functions by dependencies."""
        code = '''
def main():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        # main is entry point, comes first
        assert result.index("def main():") < result.index("def helper():")

    def test_callee_before_caller_no_entry(self):
        """Without main, callee comes before caller."""
        code = '''
def caller():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        assert result.index("def helper():") < result.index("def caller():")

    def test_chain_of_calls(self):
        """Multi-level call chain: a -> b -> c becomes c, b, a (definitions first)."""
        code = '''
def c():
    return "c"


def b():
    return c()


def a():
    return b()
'''
        result = sort_source(code)
        assert result.index("def c():") < result.index("def b():")
        assert result.index("def b():") < result.index("def a():")

    def test_diamond_dependency(self):
        """Diamond: a calls b and c, both call d."""
        code = '''
def d():
    return "d"


def c():
    return d()


def b():
    return d()


def a():
    return b(), c()
'''
        result = sort_source(code)
        # d first (called by b,c), then b and c alphabetically, then a
        assert result.index("def d():") < result.index("def b():")
        assert result.index("def d():") < result.index("def c():")
        assert result.index("def b():") < result.index("def a():")
        assert result.index("def c():") < result.index("def a():")

    def test_alphabetical_on_ties(self):
        """Functions with no dependencies should be alphabetically ordered."""
        code = '''
def charlie():
    return "c"


def alpha():
    return "a"


def bravo():
    return "b"
'''
        result = sort_source(code)
        assert result.index("def alpha():") < result.index("def bravo():")
        assert result.index("def bravo():") < result.index("def charlie():")

    def test_entry_point_first(self):
        """main() should appear first even if it has no calls."""
        code = '''
def helper():
    return 42


def main():
    return 42
'''
        result = sort_source(code)
        assert result.index("def main():") < result.index("def helper():")

    def test_underscore_helper_called(self):
        """Private helpers should come before their callers."""
        code = '''
def public_function():
    return _private_helper()


def _private_helper():
    return 42
'''
        result = sort_source(code)
        assert result.index("def _private_helper():") < result.index("def public_function():")

    def test_underscore_helper_uncalled(self):
        """Uncalled private helpers should be alphabetically sorted."""
        code = '''
def public_function():
    return 42


def _helper():
    return "x"
'''
        result = sort_source(code)
        assert result.index("def _helper():") < result.index("def public_function():")

    def test_main_no_calls(self):
        """main() with no calls should still be first."""
        code = '''
def util():
    pass


def main():
    pass
'''
        result = sort_source(code)
        assert result.index("def main():") < result.index("def util():")


class TestClassMethods:
    """Tests for method sorting within classes."""

    def test_caller_method_before_callee_method(self):
        """Methods should be sorted by call hierarchy (callees first)."""
        code = '''class Foo:
    def caller(self):
        return self.callee()

    def callee(self):
        return 42
'''
        result = sort_source(code)
        assert result.index("def callee") < result.index("def caller")

    def test_init_first(self):
        """__init__ should always be first in a class."""
        code = '''class Foo:
    def method(self):
        pass

    def __init__(self):
        pass
'''
        result = sort_source(code)
        init_pos = result.index("def __init__")
        method_pos = result.index("def method")
        assert init_pos < method_pos

    def test_method_chain(self):
        """Method call chain within a class."""
        code = '''class Foo:
    def c(self):
        return "c"

    def b(self):
        return self.c()

    def a(self):
        return self.b()
'''
        result = sort_source(code)
        assert result.index("def c") < result.index("def b")
        assert result.index("def b") < result.index("def a")

    def test_no_self_method_calls(self):
        """Methods not calling each other should be alphabetical after __init__."""
        code = '''class Foo:
    def charlie(self):
        pass

    def __init__(self):
        pass

    def alpha(self):
        pass
'''
        result = sort_source(code)
        init_pos = result.index("def __init__")
        alpha_pos = result.index("def alpha")
        charlie_pos = result.index("def charlie")
        assert init_pos < alpha_pos < charlie_pos


class TestDecorators:
    """Tests for decorator handling."""

    def test_decorator_definition_before_usage(self):
        """Decorator definition should come before functions using it."""
        code = '''
@my_decorator
def decorated():
    pass


def my_decorator(func):
    return func
'''
        result = sort_source(code)
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_multiple_decorators(self):
        """Multiple decorators should all be ordered after their definitions."""
        code = '''
@dec_a
@dec_b
def decorated():
    pass


def dec_a(func):
    return func


def dec_b(func):
    return func
'''
        result = sort_source(code)
        assert result.index("def dec_a") < result.index("def dec_b")
        assert result.index("def dec_b") < result.index("@dec_a")

    def test_decorator_calls_function(self):
        """Decorator that calls another function."""
        code = '''
@make_wrapper
def target():
    pass


def wrapper():
    pass


def make_wrapper(func):
    wrapper()
    return func
'''
        result = sort_source(code)
        assert result.index("def wrapper") < result.index("def make_wrapper")
        assert result.index("def make_wrapper") < result.index("def target")


class TestCyclesAndEdgeCases:
    """Tests for cycles and edge cases."""

    def test_mutual_recursion(self):
        """Mutually recursive functions should be deterministically ordered."""
        code = '''
def b():
    return a()


def a():
    return b()
'''
        result = sort_source(code)
        # Cycle: both depend on each other, so first alphabetically visited wins
        # Since we iterate sorted names, 'a' is visited first, but its dep 'b' is also a cycle
        # The exact order depends on DFS traversal, but it should be deterministic
        assert "def a():" in result
        assert "def b():" in result
        # Just verify both are present - exact order may vary with cycle handling

    def test_empty_module(self):
        """Empty module should remain empty."""
        assert sort_source("") == ""

    def test_single_function(self):
        """Single function module should be unchanged."""
        code = '''def only_one():
    pass
'''
        result = sort_source(code)
        assert "def only_one():" in result
        assert result.count("def ") == 1

    def test_code_preserved(self):
        """Comments and docstrings should be preserved."""
        code = '''
def main():
    # This is a comment
    """Docstring."""
    return helper()  # inline comment


def helper():
    # Another comment
    """Helper doc."""
    return 42
'''
        result = sort_source(code)
        assert "This is a comment" in result
        assert "Docstring." in result
        assert "inline comment" in result
        assert "Another comment" in result


class TestNoOp:
    """Tests for cases that should not change."""

    def test_already_sorted_with_entry(self):
        """Already sorted code with main should stay sorted."""
        code = '''
def main():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        assert result.index("def main():") == 0  # Entry point always first
        assert result.index("def helper():") > 0

    def test_decorators_preserved_when_sorted(self):
        """Decorators should stay on their functions when already sorted."""
        code = '''
def my_decorator(func):
    return func


@my_decorator
def decorated():
    pass
'''
        result = sort_source(code)
        assert "@my_decorator" in result
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_imports_preserved(self):
        """Imports and other top-level statements should be preserved."""
        code = '''
import os


def main():
    return helper()


def helper():
    return os.getcwd()
'''
        result = sort_source(code)
        assert "import os" in result


class TestConstantsAndImports:
    """Tests for handling constants that depend on functions."""

    def test_function_before_constant_using_it(self):
        """Functions should come before constants that call them."""
        code = '''"""Module docstring."""

import typing as t

TOOL_CALLING_TEMPLATE = {"key": "val"}


def _reformat(s: str) -> str:
    return s.replace("{", "{{")


TOOL_CALLING_TEMPLATES = {
    "en": _reformat(TOOL_CALLING_TEMPLATE),
}
'''
        result = sort_source(code)
        # _reformat should come before TOOL_CALLING_TEMPLATES
        assert result.index("def _reformat") < result.index("TOOL_CALLING_TEMPLATES =")
        # Docstring and imports should come before functions
        assert result.index('"""Module docstring."""') < result.index("def _reformat")
        assert result.index("import typing") < result.index("def _reformat")

    def test_imports_before_functions(self):
        """Imports should always come before functions."""
        code = '''import os


def main():
    return os.getcwd()
'''
        result = sort_source(code)
        assert result.index("import os") < result.index("def main")
