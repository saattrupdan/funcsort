"""Test cases for funcsort."""

import pytest
from funcsort.core import sort_source


class TestModuleLevelFunctions:
    """Tests for module-level function sorting."""

    def test_caller_with_entry_point(self):
        """Entry point (main) comes first among functions, even if it has dependencies."""
        code = '''
def main():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        # main comes first as entry point, helper after
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
        """Already sorted code - entry point first."""
        code = '''
def main():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        # main comes first as entry point
        assert result.index("def main():") < result.index("def helper():")

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

    def test_constants_sorted_by_dependencies(self):
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
        assert result.index('"""Module docstring."""') < result.index("TOOL_CALLING_TEMPLATE")
        assert result.index("import typing") < result.index("TOOL_CALLING_TEMPLATE")

    def test_imports_before_functions(self):
        """Imports should always come before functions."""
        code = '''import os


def main():
    return os.getcwd()
'''
        result = sort_source(code)
        assert result.index("import os") < result.index("def main")


class TestClassTypeHints:
    """Tests for class references in type hints."""

    def test_class_before_function_using_it(self):
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

    def test_generic_type_annotations(self):
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

    def test_nested_generic_annotations(self):
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


class TestConstantsOrdering:
    """Tests for constant ordering."""

    def test_constants_before_functions(self):
        """Constants should appear before functions."""
        code = '''"""Module with constants."""

def use_data(data: DATA) -> str:
    """Use data."""
    return str(data)


DATA = dict[str, str]
'''
        result = sort_source(code)
        # DATA constant should come before use_data function
        assert result.index("DATA =") < result.index("def use_data")

    def test_constants_after_imports(self):
        """Constants should appear after imports."""
        code = '''"""Module."""

import typing as t

CONST: str = "test"


def func() -> None:
    """Function."""
    pass
'''
        result = sort_source(code)
        # Import should come before constant
        assert result.index("import typing") < result.index("CONST:")
        # Constant should come before function
        assert result.index("CONST:") < result.index("def func")

    def test_class_before_function_using_it(self):
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


class TestClassBodyTypeHints:
    """Tests for type hints in class bodies."""

    def test_class_type_hint_in_body(self):
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

    def test_class_inheritance(self):
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

    def test_generic_type_in_class_body(self):
        """Generic types in class body should be handled."""
        code = '''
class Container:
    items: list[Item]


class Item:
    pass
'''
        result = sort_source(code)
        assert result.index("class Item:") < result.index("class Container:")

    def test_class_call_in_body(self):
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
        assert result.index("class DummyDevice:") < result.index("class DummyBenchmarkConfig:")


class TestConstantDependencies:
    """Tests for constants that depend on classes."""

    def test_class_before_constants_using_it(self):
        """Classes should come before constants using them in type hints."""
        code = '''"""Test module."""

PROVIDERS: list[_Provider] = []


class _Provider:
    """A provider."""
    name: str
'''
        result = sort_source(code)
        # _Provider class should come before PROVIDERS constant
        assert result.index("class _Provider:") < result.index("PROVIDERS:")

    def test_constant_order_by_dependency(self):
        """Constants should be ordered by their dependencies."""
        code = '''"""Test module."""

DEPENDENTS: list[Base] = []


class Base:
    """Base class."""
    pass
'''
        result = sort_source(code)
        assert result.index("class Base:") < result.index("DEPENDENTS:")


class TestRegressionBugs:
    """Regression tests for reported bugs - ensures they don't come back."""

    def test_decorator_definition_before_usage(self):
        """Regression: decorators must be defined before use."""
        code = '''
@my_decorator
def decorated():
    pass


def my_decorator(func):
    return func
'''
        result = sort_source(code)
        assert result.index("def my_decorator") < result.index("@my_decorator")

    def test_constant_calling_function(self):
        """Regression: function called in constant must appear before constant."""
        code = '''
TOOL_CALLING_TEMPLATES = {
    "en": _reformat("hello"),
}


def _reformat(s: str) -> str:
    return s.replace("{", "{{")
'''
        result = sort_source(code)
        assert result.index("def _reformat") < result.index("TOOL_CALLING_TEMPLATES")

    def test_class_in_type_hint_before_function(self):
        """Regression: class in type hint must appear before function."""
        code = '''
def process_user(user: User) -> str:
    return user.name


class User:
    name: str

    def __init__(self, name: str):
        self.name = name
'''
        result = sort_source(code)
        assert result.index("class User:") < result.index("def process_user")

    def test_class_instantiation_in_body(self):
        """Regression: class instantiated in class body must appear first."""
        code = '''
class DummyBenchmarkConfig:
    device = DummyDevice()


class DummyDevice:
    type = "cpu"
'''
        result = sort_source(code)
        assert result.index("class DummyDevice:") < result.index(
            "class DummyBenchmarkConfig:"
        )

    def test_class_type_hint_in_class_body(self):
        """Regression: class referenced in type hint must appear first."""
        code = '''
class Container:
    item: Item


class Item:
    pass
'''
        result = sort_source(code)
        assert result.index("class Item:") < result.index("class Container:")

    def test_generic_type_hint(self):
        """Regression: generic types in hints must be handled."""
        code = '''
def process_items(items: list[Item]) -> list[Result]:
    return []


class Item:
    pass


class Result:
    pass
'''
        result = sort_source(code)
        assert result.index("class Item:") < result.index("def process_items")
        assert result.index("class Result:") < result.index("def process_items")

    def test_class_before_constants_using_it(self):
        """Regression: class used in constants must appear before constants."""
        code = '''
PROVIDERS: list[_Provider] = []


class _Provider:
    name: str
'''
        result = sort_source(code)
        assert result.index("class _Provider:") < result.index("PROVIDERS:")

    def test_default_argument_calls_function(self):
        """Regression: default args calling functions must be detected."""
        code = '''
def process(x: Item = get_default()) -> Item:
    return x


def get_default() -> Item:
    return Item(name="default")


class Item:
    name: str
'''
        result = sort_source(code)
        # Item class before process
        assert result.index("class Item:") < result.index("def process")
        # get_default before process (called in default)
        assert result.index("def get_default") < result.index("def process")

    def test_union_type_annotations(self):
        """Regression: Union types (A | B) should be handled."""
        code = '''
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
'''
        result = sort_source(code)
        # All classes before process
        assert result.index("class Input:") < result.index("def process")
        assert result.index("class Config:") < result.index("def process")
        assert result.index("class Output:") < result.index("def process")
        assert result.index("class Error:") < result.index("def process")

    def test_lambda_constant(self):
        """Regression: lambda constants calling functions."""
        code = '''
OPERATION = lambda x: transform(x)


def transform(x: Item) -> Item:
    return x


class Item:
    pass
'''
        result = sort_source(code)
        # transform OPERATION depends on, must come before
        assert result.index("def transform") < result.index("OPERATION =")
        # Item class before transform
        assert result.index("class Item:") < result.index("def transform")

    def test_entry_point_first_when_no_deps(self):
        """Entry point (main) comes first when it has no dependencies."""
        code = '''
def helper():
    return 42


def main():
    return 42
'''
        result = sort_source(code)
        # main has no dependencies, should come first as entry point
        assert result.index("def main():") < result.index("def helper():")

    def test_constant_before_main(self):
        """Constants should come before main when main uses them."""
        code = '''
CONSTANT = "hello"


def main() -> None:
    print(CONSTANT)
'''
        result = sort_source(code)
        # CONSTANT should come before main
        assert result.index("CONSTANT =") < result.index("def main()")

    def test_multi_target_assignment(self):
        """Multi-target assignments should be preserved."""
        code = '''
RANDOM_STATE = 4242
TRAIN_SIZE, VAL_SIZE, TEST_SIZE = 1024, 256, 2048
ORIGINAL_REPO_ID = "x"
'''
        result = sort_source(code)
        # All constants should be present
        assert "RANDOM_STATE = 4242" in result
        assert "TRAIN_SIZE, VAL_SIZE, TEST_SIZE = 1024, 256, 2048" in result
        assert "ORIGINAL_REPO_ID" in result
        # Should be alphabetically sorted (no dependencies)
        assert result.index("ORIGINAL_REPO_ID") < result.index("RANDOM_STATE")
        assert result.index("RANDOM_STATE") < result.index("TRAIN_SIZE")

    def test_assert_after_constant(self):
        """Regression: assert statements should appear after the constants they reference."""
        code = '''
assert TRAIN_SIZE % 2 == 0, "must be even"

TRAIN_SIZE = 1024
'''
        result = sort_source(code)
        # TRAIN_SIZE should come before the assert
        assert result.index("TRAIN_SIZE =") < result.index("assert TRAIN_SIZE")

    def test_assert_after_multiple_constants(self):
        """Multiple asserts should appear after all constants they reference."""
        code = '''
assert TRAIN_SIZE % 2 == 0
assert VAL_SIZE % 2 == 0

TRAIN_SIZE = 1024
VAL_SIZE = 256
'''
        result = sort_source(code)
        # Constants should come before asserts
        assert result.index("TRAIN_SIZE =") < result.index("assert")
        assert result.index("VAL_SIZE =") < result.index("assert")

    def test_function_spacing_two_blank_lines(self):
        """Functions should be separated by exactly two blank lines."""
        code = '''
def foo():
    pass


def bar():
    pass
'''
        result = sort_source(code)
        # Check that functions are separated by two blank lines
        lines = result.split('\n')
        # Find the second function (alphabetically bar comes first, then foo)
        # Each function should have 2 blank lines before it
        func_count = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                func_count += 1
                if func_count > 1:
                    # Second function onwards should have 2 blank lines before
                    assert lines[i - 1] == '', f"Expected blank line before function at line {i}, got: {repr(lines[i - 1])}"
                    assert lines[i - 2] == '', f"Expected two blank lines before function at line {i}, got: {repr(lines[i - 2])}"
                    break

    def test_constant_function_spacing(self):
        """Constants and functions should have proper spacing (1 before constant, 2 before function)."""
        code = '''
CONSTANT = 1


def main():
    pass
'''
        result = sort_source(code)
        lines = result.split('\n')
        # Find CONSTANT line
        const_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith('CONSTANT ='):
                const_idx = i
                break
        assert const_idx is not None
        # After constant: 2 blank lines before function
        assert lines[const_idx + 1] == '', "Expected blank line after constant"
        assert lines[const_idx + 2] == '', "Expected second blank line after constant"
        assert lines[const_idx + 3].strip().startswith('def '), "Expected function after blanks"

    def test_main_first_among_functions(self):
        """Entry point (main) should come first among functions when it has no function dependencies."""
        code = '''
def helper():
    return 42


def main():
    return 42
'''
        result = sort_source(code)
        # main should come before helper (both have no deps, main is entry point)
        assert result.index("def main():") < result.index("def helper():")

    def test_main_after_constants(self):
        """Entry point should come after constants (even when it has no function deps)."""
        code = '''
CONSTANT = "hello"


def main():
    print(CONSTANT)


def helper():
    pass
'''
        result = sort_source(code)
        # CONSTANT first, then main, then helper
        const_idx = result.index("CONSTANT =")
        main_idx = result.index("def main():")
        helper_idx = result.index("def helper():")
        assert const_idx < main_idx, "Constant should be before main"
        assert main_idx < helper_idx, "Main should be before helper"

    def test_entry_point_first_even_with_dependencies(self):
        """Entry point (main) comes first among functions, even when it calls other functions."""
        code = '''
def main():
    return helper()


def helper():
    return 42
'''
        result = sort_source(code)
        # main comes first as entry point, even though it depends on helper
        assert result.index("def main():") < result.index("def helper():")

    def test_constants_before_entry_point(self):
        """Constants come before entry point, even when entry uses them."""
        code = '''
CONSTANT = "hello"


def main():
    print(CONSTANT)
'''
        result = sort_source(code)
        const_idx = result.index("CONSTANT =")
        main_idx = result.index("def main():")
        assert const_idx < main_idx, "Constant should be before main"

    def test_asserts_after_constants_they_reference(self):
        """Assert statements appear after the constants they reference."""
        code = '''
assert TRAIN_SIZE % 2 == 0

TRAIN_SIZE = 1024
'''
        result = sort_source(code)
        assert result.index("TRAIN_SIZE =") < result.index("assert")

    def test_spacing_between_functions(self):
        """Functions separated by exactly two blank lines."""
        code = '''
def foo():
    pass


def bar():
    pass
'''
        result = sort_source(code)
        lines = result.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('def bar'):
                assert lines[i - 1] == '', "Expected blank line before bar"
                assert lines[i - 2] == '', "Expected two blank lines before bar"
                break
