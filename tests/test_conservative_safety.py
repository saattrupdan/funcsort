"""Regression tests for conservative, safety-preserving sorting.

funcsort must never reorder in a way that breaks working code: constants, imports
and module-level statements stay put, and functions/classes are only reordered
when it preserves definition-time name resolution.
"""

from funcsort.core import sort_source


class TestDefinitionTimeSafety:
    """Reordering must preserve names needed at definition time."""

    def test_class_used_in_method_annotation_stays_before_user(self) -> None:
        """A class used in another class's method signature comes first."""
        code = """class DatasetConfig:
    def __init__(self, task: Task) -> None:
        self.task = task


class Task:
    name: str
"""
        result = sort_source(code)
        assert result.index("class Task") < result.index("class DatasetConfig")
        compile(result, "result", "exec")

    def test_constants_between_functions_are_not_moved(self) -> None:
        """A constant between two functions stays exactly where it is."""
        code = """def first() -> int:
    return 1


CONSTANT = first()


def second() -> int:
    return 2
"""
        result = sort_source(code)
        # first() must stay before CONSTANT (which calls it at module load).
        assert result.index("def first") < result.index("CONSTANT =")
        assert result.index("CONSTANT =") < result.index("def second")
        compile(result, "result", "exec")

    def test_function_used_as_class_default_stays_before_class(self) -> None:
        """A function called in a class body must remain before that class."""
        code = """def get_version(name: str) -> str:
    return name


class Result:
    version: str = get_version("x")
"""
        result = sort_source(code)
        assert result.index("def get_version") < result.index("class Result")
        compile(result, "result", "exec")

    def test_property_getter_before_setter(self) -> None:
        """A property getter must stay before its setter."""
        code = """class Config:
    def __init__(self) -> None:
        self._name = ""

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
"""
        result = sort_source(code)
        assert result.index("@property") < result.index("@name.setter")
        # No blank line should carry trailing whitespace.
        assert not any(line != "" and line.strip() == "" for line in result.split("\n"))
        compile(result, "result", "exec")

    def test_trailing_newline_is_preserved_with_uv_header(self) -> None:
        """The uv-script header path must not strip the file's trailing newline.

        Regression: extracting the ``# /// script ... # ///`` header via
        ``splitlines`` dropped the final newline, so the end-of-file-fixer
        pre-commit hook then re-added it on every run.
        """
        code = """# /// script
# dependencies = []
# ///
def b() -> int:
    return a()


def a() -> int:
    return 1
"""
        result = sort_source(code)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")
        # A file without a trailing newline must likewise stay that way.
        assert not sort_source(code.rstrip("\n")).endswith("\n")


class TestNoOpWithoutDefinitions:
    """Files with no top-level functions/classes must be left untouched."""

    def test_module_of_statements_is_unchanged(self) -> None:
        """Imports, if-blocks, calls and assignments keep their exact positions.

        Regression: an ``__init__`` module with staged imports and a ``fmt``
        variable used by ``logging.basicConfig`` was scrambled - imports were
        hoisted and ``fmt`` was moved after its use.
        """
        code = '''"""Package init."""

import logging
import os

if os.getenv("FULL_LOG") != "1":
    logging.getLogger("httpx").setLevel(logging.CRITICAL)

fmt = "%(message)s"
logging.basicConfig(format=fmt)

import importlib.metadata  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

__version__ = importlib.metadata.version("euroeval")

os.environ["X"] = "1"
'''
        assert sort_source(code) == code
