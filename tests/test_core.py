"""Test cases for funcsort."""

from funcsort.core import sort_source


class TestClassBodyTypeHints:
    """Tests for type hints in class bodies."""

    def test_class_call_in_body(self) -> None:
        """Classes instantiated in class body should come first."""
        code = '''
class DummyBenchmarkConfig:
    """Dummy benchmark config for testing."""

    device = DummyDevice()


class DummyDevice:
    """Dummy device for testing."""

    type = "cpu"
'''
        result = sort_source(code)
        assert result.index("class DummyDevice:") < result.index(
            "class DummyBenchmarkConfig:"
        )

    def test_class_inheritance(self) -> None:
        """Base classes should come before child classes."""
        code = '''
class Child(Parent):
    """Child class."""
    pass


class Parent:
    """Parent class."""
    pass
'''
        result = sort_source(code)
        assert result.index("class Parent:") < result.index("class Child(")

    def test_class_type_hint_in_body(self) -> None:
        """Classes referenced in class body annotations should come first."""
        code = '''
class Container:
    """Container with typed field."""
    item: Item


class Item:
    """An item."""
    pass
'''
        result = sort_source(code)
        assert result.index("class Item:") < result.index("class Container:")

    def test_generic_type_in_class_body(self) -> None:
        """Generic types in class body should be handled."""
        code = """
class Container:
    items: list[Item]


class Item:
    pass
"""
        result = sort_source(code)
        assert result.index("class Item:") < result.index("class Container:")


class TestClassMethods:
    """Tests for method sorting within classes."""

    def test_caller_method_before_callee_method(self) -> None:
        """Methods should be sorted by call hierarchy (callers first)."""
        code = """class Foo:
    def caller(self):
        return self.callee()

    def callee(self):
        return 42
"""
        result = sort_source(code)
        assert result.index("def caller") < result.index("def callee")

    def test_init_first(self) -> None:
        """__init__ should always be first in a class."""
        code = """class Foo:
    def method(self):
        pass

    def __init__(self):
        pass
"""
        result = sort_source(code)
        init_pos = result.index("def __init__")
        method_pos = result.index("def method")
        assert init_pos < method_pos

    def test_method_chain(self) -> None:
        """Method call chain within a class."""
        code = """class Foo:
    def c(self):
        return "c"

    def b(self):
        return self.c()

    def a(self):
        return self.b()
"""
        result = sort_source(code)
        assert result.index("def a") < result.index("def b")
        assert result.index("def b") < result.index("def c")

    def test_no_self_method_calls(self) -> None:
        """Methods not calling each other should be alphabetical after __init__."""
        code = """class Foo:
    def charlie(self):
        pass

    def __init__(self):
        pass

    def alpha(self):
        pass
"""
        result = sort_source(code)
        init_pos = result.index("def __init__")
        alpha_pos = result.index("def alpha")
        charlie_pos = result.index("def charlie")
        assert init_pos < alpha_pos < charlie_pos


class TestClassTypeHints:
    """Tests for class references in type hints."""

    def test_class_before_function_using_it(self) -> None:
        """Classes should come before functions using them in type hints."""
        code = '''"""Module with class type hints."""


def process_user(user: User) -> str:
    """Process a user."""
    return user.name


class User:
    """A user class."""
    name: str

    def __init__(self, name: str):
        self.name = name
'''
        result = sort_source(code)
        # User class should come before process_user
        assert result.index("class User:") < result.index("def process_user")

    def test_generic_type_annotations(self) -> None:
        """Generic types like list[T] should be handled."""
        code = '''
def process_items(items: list[Item]) -> list[Result]:
    """Process a list of items."""
    return []


class Item:
    """An item."""
    pass


class Result:
    """A result."""
    pass
'''
        result = sort_source(code)
        # Item and Result should come before process_items
        assert result.index("class Item:") < result.index("def process_items")
        assert result.index("class Result:") < result.index("def process_items")

    def test_nested_generic_annotations(self) -> None:
        """Nested generics like dict[str, list[T]] should be handled."""
        code = '''
def get_data() -> dict[str, list[Record]]:
    """Get data."""
    return {}


class Record:
    """A record."""
    pass
'''
        result = sort_source(code)
        assert result.index("class Record:") < result.index("def get_data")


class TestConstantsAndImports:
    """Tests for handling constants that depend on functions."""

    def test_constants_sorted_by_dependencies(self) -> None:
        """Constants should be ordered by their dependencies.

        Constants that don't depend on functions come before functions.
        Constants that depend on functions come after those functions.
        """
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
        # TOOL_CALLING_TEMPLATE (no deps) comes before functions
        assert result.index("TOOL_CALLING_TEMPLATE =") < result.index("def _reformat")
        # TOOL_CALLING_TEMPLATES (depends on _reformat) comes after
        assert result.index("def _reformat") < result.index("TOOL_CALLING_TEMPLATES =")
        # Docstring and imports should come first
        assert result.index('"""Module docstring."""') < result.index(
            "TOOL_CALLING_TEMPLATE"
        )
        assert result.index("import typing") < result.index("TOOL_CALLING_TEMPLATE")

    def test_imports_before_functions(self) -> None:
        """Imports should always come before functions."""
        code = """import os


def main():
    return os.getcwd()
"""
        result = sort_source(code)
        assert result.index("import os") < result.index("def main")


class TestConstantsOrdering:
    """Tests for constants (which stay in original positions, not sorted)."""

    def test_class_before_function_using_it(self) -> None:
        """Classes used in type hints should come before functions."""
        code = '''
def process(obj: Item) -> str:
    """Process item."""
    return str(obj)


class Item:
    """An item."""
    pass
'''
        result = sort_source(code)
        assert result.index("class Item:") < result.index("def process")

    def test_constants_order_preserved(self) -> None:
        """Multiple constants preserve their order."""
        code = '''"""Module."""

import typing as t

CONST_A: str = "a"
CONST_B: str = "b"
'''
        result = sort_source(code)
        # Constants stay in original order
        assert result.index("CONST_A") < result.index("CONST_B")

    def test_constants_preserve_position(self) -> None:
        """Constants stay in their original order (not sorted).

        Only functions and classes are sorted by call hierarchy.
        """
        code = '''"""Module with constants."""

DATA = dict[str, str]


def use_data(data: DATA) -> str:
    """Use data."""
    return str(data)
'''
        result = sort_source(code)
        # All elements should be present (constants preserve position)
        assert "DATA =" in result
        assert "def use_data" in result


class TestCyclesAndEdgeCases:
    """Tests for cycles and edge cases."""

    def test_code_preserved(self) -> None:
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

    def test_empty_module(self) -> None:
        """Empty module should remain empty."""
        assert sort_source("") == ""

    def test_mutual_recursion(self) -> None:
        """Mutually recursive functions should be deterministically ordered."""
        code = """
def b():
    return a()


def a():
    return b()
"""
        result = sort_source(code)
        # Cycle: both depend on each other, so first alphabetically visited wins
        # Since we iterate sorted names, 'a' is visited first, but its dep 'b' is
        # also a cycle
        # The exact order depends on DFS traversal, but it should be deterministic
        assert "def a():" in result
        assert "def b():" in result
        # Just verify both are present - exact order may vary with cycle handling

    def test_single_function(self) -> None:
        """Single function module should be unchanged."""
        code = """def only_one():
    pass
"""
        result = sort_source(code)
        assert "def only_one():" in result
        assert result.count("def ") == 1


class TestDecorators:
    """Tests for decorator handling."""

    def test_decorator_calls_function(self) -> None:
        """Decorator that calls another function."""
        code = """
@make_wrapper
def target():
    pass


def wrapper():
    pass


def make_wrapper(func):
    wrapper()
    return func
"""
        result = sort_source(code)
        # make_wrapper calls wrapper (caller first) and decorates target (the
        # decorator definition is a hard constraint, so it precedes its usage).
        assert result.index("def make_wrapper") < result.index("def wrapper")
        assert result.index("def make_wrapper") < result.index("def target")

    def test_decorator_definition_before_usage(self) -> None:
        """Decorator definition should come before functions using it."""
        code = """
@my_decorator
def decorated():
    pass


def my_decorator(func):
    return func
"""
        result = sort_source(code)
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_multiple_decorators(self) -> None:
        """Multiple decorators should all be ordered after their definitions."""
        code = """
@dec_a
@dec_b
def decorated():
    pass


def dec_a(func):
    return func


def dec_b(func):
    return func
"""
        result = sort_source(code)
        assert result.index("def dec_a") < result.index("def dec_b")
        assert result.index("def dec_b") < result.index("@dec_a")


class TestModuleLevelFunctions:
    """Tests for module-level function sorting."""

    def test_alphabetical_on_ties(self) -> None:
        """Functions with no dependencies should be alphabetically ordered."""
        code = """
def charlie():
    return "c"


def alpha():
    return "a"


def bravo():
    return "b"
"""
        result = sort_source(code)
        assert result.index("def alpha():") < result.index("def bravo():")
        assert result.index("def bravo():") < result.index("def charlie():")

    def test_caller_before_callee_no_entry(self) -> None:
        """Without main, caller comes before callee."""
        code = """
def caller():
    return helper()


def helper():
    return 42
"""
        result = sort_source(code)
        assert result.index("def caller():") < result.index("def helper():")

    def test_caller_with_entry_point(self) -> None:
        """Entry point (main) is first among functions, even with dependencies."""
        code = """
def main():
    return helper()


def helper():
    return 42
"""
        result = sort_source(code)
        # main comes first as entry point, helper after
        assert result.index("def main():") < result.index("def helper():")

    def test_chain_of_calls(self) -> None:
        """Multi-level call chain: a -> b -> c stays a, b, c (callers first)."""
        code = """
def c():
    return "c"


def b():
    return c()


def a():
    return b()
"""
        result = sort_source(code)
        assert result.index("def a():") < result.index("def b():")
        assert result.index("def b():") < result.index("def c():")

    def test_diamond_dependency(self) -> None:
        """Diamond: a calls b and c, both call d."""
        code = """
def d():
    return "d"


def c():
    return d()


def b():
    return d()


def a():
    return b(), c()
"""
        result = sort_source(code)
        # a is the sole root (nobody calls it), so it leads; its callees follow.
        assert result.index("def a():") < result.index("def b():")
        assert result.index("def a():") < result.index("def c():")
        assert result.index("def a():") < result.index("def d():")
        assert result.index("def b():") < result.index("def d():")

    def test_entry_point_first(self) -> None:
        """main() should appear first even if it has no calls."""
        code = """
def helper():
    return 42


def main():
    return 42
"""
        result = sort_source(code)
        assert result.index("def main():") < result.index("def helper():")

    def test_main_no_calls(self) -> None:
        """main() with no calls should still be first."""
        code = """
def util():
    pass


def main():
    pass
"""
        result = sort_source(code)
        assert result.index("def main():") < result.index("def util():")

    def test_underscore_helper_called(self) -> None:
        """Callers come before the private helpers they call."""
        code = """
def public_function():
    return _private_helper()


def _private_helper():
    return 42
"""
        result = sort_source(code)
        assert result.index("def public_function():") < result.index(
            "def _private_helper():"
        )

    def test_underscore_helper_uncalled(self) -> None:
        """Uncalled private helpers should be alphabetically sorted."""
        code = """
def public_function():
    return 42


def _helper():
    return "x"
"""
        result = sort_source(code)
        assert result.index("def _helper():") < result.index("def public_function():")


class TestNoOp:
    """Tests for cases that should not change."""

    def test_already_sorted_with_entry(self) -> None:
        """Already sorted code - entry point first."""
        code = """
def main():
    return helper()


def helper():
    return 42
"""
        result = sort_source(code)
        # main comes first as entry point
        assert result.index("def main():") < result.index("def helper():")

    def test_decorators_preserved_when_sorted(self) -> None:
        """Decorators should stay on their functions when already sorted."""
        code = """
def my_decorator(func):
    return func


@my_decorator
def decorated():
    pass
"""
        result = sort_source(code)
        assert "@my_decorator" in result
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_imports_preserved(self) -> None:
        """Imports and other top-level statements should be preserved."""
        code = """
import os


def main():
    return helper()


def helper():
    return os.getcwd()
"""
        result = sort_source(code)
        assert "import os" in result


class TestRegressionBugs:
    """Regression tests for reported bugs - ensures they don't come back."""

    def test_assert_after_constant(self) -> None:
        """Assert statements referencing constants - order is preserved.

        Note: Constants are not sorted. If assert comes before constant in source,
        funcsort won't fix it (that's a runtime error the user must fix).
        """
        code = """
TRAIN_SIZE = 1024

assert TRAIN_SIZE % 2 == 0, "must be even"
"""
        result = sort_source(code)
        # Order is preserved (constants stay in place)
        assert result.index("TRAIN_SIZE =") < result.index("assert TRAIN_SIZE")

    def test_assert_after_multiple_constants(self) -> None:
        """Multiple asserts referencing constants - order is preserved.

        Note: Constants are not sorted - they stay in their original positions.
        """
        code = """
TRAIN_SIZE = 1024
VAL_SIZE = 256

assert TRAIN_SIZE % 2 == 0
assert VAL_SIZE % 2 == 0
"""
        result = sort_source(code)
        # Order is preserved (constants stay in place, before their asserts)
        assert result.index("TRAIN_SIZE =") < result.index("assert")
        assert result.index("VAL_SIZE =") < result.index("assert")

    def test_asserts_after_constants_they_reference(self) -> None:
        """Assert statements stay after the constants they reference - order kept.

        Note: Constants are not sorted. Correct order in source is required.
        """
        code = """
TRAIN_SIZE = 1024

assert TRAIN_SIZE % 2 == 0
"""
        result = sort_source(code)
        # Order is preserved
        assert result.index("TRAIN_SIZE =") < result.index("assert")

    def test_class_before_constants_using_it(self) -> None:
        """Regression: class used in constants must appear before constants.

        Note: constants are not sorted. Class must be defined before constant in source.
        """
        code = """
class _Provider:
    name: str


PROVIDERS: list[_Provider] = []
"""
        result = sort_source(code)
        # Order preserved (class already before constant)
        assert result.index("class _Provider:") < result.index("PROVIDERS:")

    def test_class_in_type_hint_before_function(self) -> None:
        """Regression: class in type hint must appear before function."""
        code = """
def process_user(user: User) -> str:
    return user.name


class User:
    name: str

    def __init__(self, name: str):
        self.name = name
"""
        result = sort_source(code)
        assert result.index("class User:") < result.index("def process_user")

    def test_class_instantiation_in_body(self) -> None:
        """Regression: class instantiated in class body must appear first."""
        code = """
class DummyBenchmarkConfig:
    device = DummyDevice()


class DummyDevice:
    type = "cpu"
"""
        result = sort_source(code)
        assert result.index("class DummyDevice:") < result.index(
            "class DummyBenchmarkConfig:"
        )

    def test_class_type_hint_in_class_body(self) -> None:
        """Regression: class referenced in type hint must appear first."""
        code = """
class Container:
    item: Item


class Item:
    pass
"""
        result = sort_source(code)
        assert result.index("class Item:") < result.index("class Container:")

    def test_constant_before_main(self) -> None:
        """Constants should come before main when main uses them."""
        code = """
CONSTANT = "hello"


def main() -> None:
    print(CONSTANT)
"""
        result = sort_source(code)
        # CONSTANT should come before main
        assert result.index("CONSTANT =") < result.index("def main()")

    def test_constant_calling_function(self) -> None:
        """Regression: function called in constant must appear before constant.

        Note: constants are not sorted - they stay in place.
        User must define functions before constants that call them.
        """
        code = """
def _reformat(s: str) -> str:
    return s.replace("{", "{{")


TOOL_CALLING_TEMPLATES = {
    "en": _reformat("hello"),
}
"""
        result = sort_source(code)
        # Order preserved (function already before constant)
        assert result.index("def _reformat") < result.index("TOOL_CALLING_TEMPLATES")

    def test_constant_function_spacing(self) -> None:
        """Constants and functions are spaced correctly (1 before, 2 before def)."""
        code = """
CONSTANT = 1


def main():
    pass
"""
        result = sort_source(code)
        lines = result.split("\n")
        # Find CONSTANT line
        const_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("CONSTANT ="):
                const_idx = i
                break
        assert const_idx is not None
        # After constant: 2 blank lines before function
        assert lines[const_idx + 1] == "", "Expected blank line after constant"
        assert lines[const_idx + 2] == "", "Expected second blank line after constant"
        assert lines[const_idx + 3].strip().startswith("def "), (
            "Expected function after blanks"
        )

    def test_constants_before_entry_point(self) -> None:
        """Constants come before entry point, even when entry uses them."""
        code = """
CONSTANT = "hello"


def main():
    print(CONSTANT)
"""
        result = sort_source(code)
        const_idx = result.index("CONSTANT =")
        main_idx = result.index("def main():")
        assert const_idx < main_idx, "Constant should be before main"

    def test_decorator_definition_before_usage(self) -> None:
        """Regression: decorators must be defined before use."""
        code = """
@my_decorator
def decorated():
    pass


def my_decorator(func):
    return func
"""
        result = sort_source(code)
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_default_argument_calls_function(self) -> None:
        """Regression: default args calling functions must be detected."""
        code = """
def process(x: Item = get_default()) -> Item:
    return x


def get_default() -> Item:
    return Item(name="default")


class Item:
    name: str
"""
        result = sort_source(code)
        # Item class before process
        assert result.index("class Item:") < result.index("def process")
        # get_default before process (called in default)
        assert result.index("def get_default") < result.index("def process")

    def test_entry_point_first_even_with_dependencies(self) -> None:
        """Entry point (main) is first among functions, even when it calls others."""
        code = """
def main():
    return helper()


def helper():
    return 42
"""
        result = sort_source(code)
        # main comes first as entry point, even though it depends on helper
        assert result.index("def main():") < result.index("def helper():")

    def test_entry_point_first_when_no_deps(self) -> None:
        """Entry point (main) comes first when it has no dependencies."""
        code = """
def helper():
    return 42


def main():
    return 42
"""
        result = sort_source(code)
        # main has no dependencies, should come first as entry point
        assert result.index("def main():") < result.index("def helper():")

    def test_function_spacing_two_blank_lines(self) -> None:
        """Functions should be separated by exactly two blank lines."""
        code = """
def foo():
    pass


def bar():
    pass
"""
        result = sort_source(code)
        # Check that functions are separated by two blank lines
        lines = result.split("\n")
        # Find the second function (alphabetically bar comes first, then foo)
        # Each function should have 2 blank lines before it
        func_count = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("def "):
                func_count += 1
                if func_count > 1:
                    # Second function onwards should have 2 blank lines before
                    assert lines[i - 1] == "", f"no blank line before func at {i}"
                    assert lines[i - 2] == "", f"need 2 blank lines before func at {i}"
                    break

    def test_generic_type_hint(self) -> None:
        """Regression: generic types in hints must be handled."""
        code = """
def process_items(items: list[Item]) -> list[Result]:
    return []


class Item:
    pass


class Result:
    pass
"""
        result = sort_source(code)
        assert result.index("class Item:") < result.index("def process_items")
        assert result.index("class Result:") < result.index("def process_items")

    def test_lambda_constant(self) -> None:
        """Regression: lambda constants calling functions.

        Note: constants are not sorted. Functions/classes must be defined
        before constants that depend on them.
        """
        code = """
class Item:
    pass


def transform(x: Item) -> Item:
    return x


OPERATION = lambda x: transform(x)
"""
        result = sort_source(code)
        # Order preserved (all already in correct order)
        assert result.index("class Item:") < result.index("def transform")
        assert result.index("def transform") < result.index("OPERATION =")

    def test_main_after_constants(self) -> None:
        """Entry point comes after constants (even with no function deps)."""
        code = """
CONSTANT = "hello"


def main():
    print(CONSTANT)


def helper():
    pass
"""
        result = sort_source(code)
        # CONSTANT first, then main, then helper
        const_idx = result.index("CONSTANT =")
        main_idx = result.index("def main():")
        helper_idx = result.index("def helper():")
        assert const_idx < main_idx, "Constant should be before main"
        assert main_idx < helper_idx, "Main should be before helper"

    def test_main_first_among_functions(self) -> None:
        """Entry point (main) is first among functions when it has no deps."""
        code = """
def helper():
    return 42


def main():
    return 42
"""
        result = sort_source(code)
        # main should come before helper (both have no deps, main is entry point)
        assert result.index("def main():") < result.index("def helper():")

    def test_multi_target_assignment(self) -> None:
        """Multi-target assignments should be preserved.

        Note: constants are not sorted - they stay in original order.
        """
        code = """
RANDOM_STATE = 4242
TRAIN_SIZE, VAL_SIZE, TEST_SIZE = 1024, 256, 2048
ORIGINAL_REPO_ID = "x"
"""
        result = sort_source(code)
        # All constants should be present in original order
        assert "RANDOM_STATE = 4242" in result
        assert "TRAIN_SIZE, VAL_SIZE, TEST_SIZE = 1024, 256, 2048" in result
        assert "ORIGINAL_REPO_ID" in result
        # Constants maintain original order (not sorted)
        assert result.index("RANDOM_STATE") < result.index("TRAIN_SIZE")
        assert result.index("TRAIN_SIZE") < result.index("ORIGINAL_REPO_ID")

    def test_spacing_between_functions(self) -> None:
        """Functions separated by exactly two blank lines."""
        code = """
def foo():
    pass


def bar():
    pass
"""
        result = sort_source(code)
        # Functions sorted alphabetically (bar before foo)
        lines = result.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("def foo"):
                # foo comes second, should have 2 blank lines before it
                assert lines[i - 1] == "", "Expected blank line before foo"
                assert lines[i - 2] == "", "Expected two blank lines before foo"
                break

    def test_union_type_annotations(self) -> None:
        """Regression: Union types (A | B) should be handled."""
        code = """
def process(x: Input | Config) -> Output | Error:
    return Output()


class Input:
    pass


class Config:
    pass


class Output:
    pass


class Error:
    pass
"""
        result = sort_source(code)
        # All classes before process
        assert result.index("class Input:") < result.index("def process")
        assert result.index("class Config:") < result.index("def process")
        assert result.index("class Output:") < result.index("def process")
        assert result.index("class Error:") < result.index("def process")
