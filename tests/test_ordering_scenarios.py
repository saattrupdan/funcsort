"""Public-interface ordering scenarios with complete Python definitions."""

import ast
import itertools
import typing as t
from dataclasses import dataclass

import pytest

from funcsort.core import sort_source


@dataclass(frozen=True)
class _Scenario:
    """A complete input module and its expected definition sequence."""

    name: str
    blocks: tuple[str, ...]
    expected: tuple[str, ...]
    permute: bool = True
    xfail: str | None = None


SCENARIOS = (
    _Scenario(
        "chain",
        (
            "def leaf():\n    return 1",
            "def middle():\n    return leaf()",
            "def root():\n    return middle()",
        ),
        ("root", "middle", "leaf"),
    ),
    _Scenario(
        "confirmed_main_siblings",
        (
            "def parse():\n    return 1",
            "def load():\n    return parse()",
            "def save():\n    return 2",
            "def main():\n    load()\n    save()",
        ),
        ("main", "load", "save", "parse"),
        xfail="Confirmed sibling order is not met.",
    ),
    _Scenario(
        "independent_alpha_beta",
        (
            "def alpha_helper():\n    return 1",
            "def alpha():\n    return alpha_helper()",
            "def beta_helper():\n    return 2",
            "def beta():\n    return beta_helper()",
        ),
        ("alpha", "beta", "alpha_helper", "beta_helper"),
        xfail="Confirmed independent-root order is not met.",
    ),
    _Scenario(
        "shared_helper_unequal_depths",
        (
            "def shared():\n    return 1",
            "def shallow():\n    return shared()",
            "def deep():\n    return shared()",
            "def branch():\n    return deep()",
            "def main():\n    shallow()\n    branch()",
        ),
        ("main", "branch", "shallow", "deep", "shared"),
        xfail="Confirmed breadth order is not met.",
    ),
    _Scenario(
        "diamond",
        (
            "def finish():\n    return 1",
            "def left():\n    return finish()",
            "def right():\n    return finish()",
            "def start():\n    left()\n    right()",
        ),
        ("start", "left", "right", "finish"),
        xfail="Confirmed sibling order is not met.",
    ),
    _Scenario(
        "three_level_siblings",
        (
            "def deep():\n    return 1",
            "def branch():\n    return deep()",
            "def sibling():\n    return 2",
            "def root():\n    branch()\n    sibling()",
        ),
        ("root", "branch", "sibling", "deep"),
        xfail="Confirmed sibling order is not met.",
    ),
    _Scenario(
        "alphabetical_independent_roots",
        (
            "def zeta():\n    return 1",
            "def alpha():\n    return 2",
            "def middle():\n    return 3",
        ),
        ("alpha", "middle", "zeta"),
    ),
    _Scenario(
        "main_entry_point",
        ("def helper():\n    return 1", "def main():\n    return helper()"),
        ("main", "helper"),
    ),
    _Scenario(
        "init_entry_point",
        ("def helper():\n    return 1", "def __init__():\n    return helper()"),
        ("__init__", "helper"),
    ),
    _Scenario(
        "caller_without_entry",
        ("def callee():\n    return 1", "def caller():\n    return callee()"),
        ("caller", "callee"),
    ),
    _Scenario(
        "underscore_helper",
        ("def _helper():\n    return 1", "def public():\n    return _helper()"),
        ("public", "_helper"),
    ),
    _Scenario(
        "mutual_cycle",
        ("def zebra():\n    return alpha()", "def alpha():\n    return zebra()"),
        ("alpha", "zebra"),
    ),
    _Scenario(
        "three_node_cycle",
        (
            "def gamma():\n    return beta()",
            "def beta():\n    return alpha()",
            "def alpha():\n    return gamma()",
        ),
        ("alpha", "beta", "gamma"),
        xfail="Confirmed alphabetical cycle order is not met.",
    ),
    _Scenario(
        "async_await_chain",
        (
            "async def fetch_data():\n    return 1",
            "async def prepare():\n    return await fetch_data()",
            "async def main():\n    return await prepare()",
        ),
        ("main", "prepare", "fetch_data"),
    ),
    _Scenario(
        "real_class_self_methods",
        (
            """class Worker:
    def unused(self):
        return 1

    def finish(self):
        return 2

    def work(self):
        return self.finish()

    def __init__(self):
        self.work()""",
        ),
        ("Worker", "Worker.__init__", "Worker.unused", "Worker.work", "Worker.finish"),
        xfail="Confirmed method roots precede helpers.",
    ),
    _Scenario(
        "class_method_chain",
        (
            """class Worker:
    def z_finish(self):
        return 1

    def b_work(self):
        return self.z_finish()

    def a_start(self):
        return self.b_work()""",
        ),
        ("Worker", "Worker.a_start", "Worker.b_work", "Worker.z_finish"),
    ),
    _Scenario(
        "callback_sorted_key",
        (
            "def alpha(value):\n    return value",
            "def zebra(values):\n    return sorted(values, key=alpha)",
        ),
        ("zebra", "alpha"),
        xfail="Confirmed callback dependency is not ordered yet.",
    ),
    _Scenario(
        "callback_map",
        (
            "def alpha(value):\n    return value",
            "def zebra(values):\n    return map(alpha, values)",
        ),
        ("zebra", "alpha"),
        xfail="Confirmed callback dependency is not ordered yet.",
    ),
    _Scenario(
        "callback_executor",
        (
            "def alpha(value):\n    return value",
            "def zebra(executor):\n    return executor.submit(alpha, 1)",
        ),
        ("zebra", "alpha"),
        xfail="Confirmed callback dependency is not ordered yet.",
    ),
    _Scenario(
        "default_factory_safety",
        (
            "def factory():\n    return 1",
            "def consumer(value=factory()):\n    return value",
        ),
        ("factory", "consumer"),
        permute=False,
    ),
    _Scenario(
        "annotation_class_safety",
        (
            "class Model:\n    pass",
            "def main(value: Model) -> Model:\n    return value",
        ),
        ("Model", "main"),
        permute=False,
    ),
    _Scenario(
        "decorator_definition_safety",
        (
            "def z_decorate(function):\n    return function",
            "@z_decorate\ndef alpha():\n    return 1",
        ),
        ("z_decorate", "alpha"),
        permute=False,
    ),
    _Scenario(
        "base_class_safety",
        ("class ZBase:\n    pass", "class AChild(ZBase):\n    pass"),
        ("ZBase", "AChild"),
        permute=False,
    ),
    _Scenario(
        "metaclass_safety",
        ("class ZMeta(type):\n    pass", "class AThing(metaclass=ZMeta):\n    pass"),
        ("ZMeta", "AThing"),
        permute=False,
    ),
    _Scenario(
        "class_body_default_safety",
        ("def factory():\n    return 1", "class Container:\n    value = factory()"),
        ("factory", "Container"),
        permute=False,
    ),
    _Scenario(
        "property_getter_setter_chain",
        (
            """class Item:
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value""",
        ),
        ("Item", "Item.value", "Item.value"),
        permute=False,
    ),
    _Scenario(
        "property_getter_setter_precedes_user",
        (
            """class Item:
    def display(self):
        return self.value

    @property
    def value(self):
        return 1

    @value.setter
    def value(self, value):
        self._value = value""",
        ),
        ("Item", "Item.display", "Item.value", "Item.value"),
        permute=False,
    ),
    _Scenario(
        "mixed_function_and_class_calls",
        (
            "def finish():\n    return 1",
            "class Worker:\n    def run(self):\n        return finish()",
            "def main():\n    Worker().run()",
        ),
        ("main", "Worker", "Worker.run", "finish"),
    ),
    _Scenario(
        "external_attribute_call_ignored",
        (
            "def alpha():\n    return 1",
            "def zebra(service):\n    return service.alpha()",
        ),
        ("alpha", "zebra"),
        xfail="External attribute calls incorrectly match local definition names.",
    ),
    _Scenario(
        "nested_function_order_preserved",
        (
            """def outer():
    def z_inner():
        return a_inner()

    def a_inner():
        return 1

    return z_inner()""",
            "def main():\n    return outer()",
        ),
        ("main", "outer"),
    ),
    _Scenario(
        "statement_anchor_and_main_guard",
        (
            "def zebra():\n    return 1",
            "VALUE = 1",
            "def beta():\n    return 2",
            "def alpha():\n    return 3",
            "if __name__ == '__main__':\n    beta()",
        ),
        ("zebra", "alpha", "beta"),
        permute=False,
    ),
    _Scenario(
        "class_static_methods",
        (
            """class Service:
    @staticmethod
    def make():
        return Service.build()

    @classmethod
    def build(cls):
        return cls()""",
        ),
        ("Service", "Service.make", "Service.build"),
    ),
    _Scenario(
        "unused_root_before_helpers",
        (
            "def helper():\n    return 1",
            "def alpha():\n    return helper()",
            "def unused():\n    return 2",
        ),
        ("alpha", "unused", "helper"),
        xfail="Confirmed roots precede helper definitions.",
    ),
    _Scenario(
        "decorated_class_method",
        (
            "def decorate(function):\n    return function",
            "class Worker:\n    @decorate\n    def run(self):\n        return 1",
        ),
        ("decorate", "Worker", "Worker.run"),
        permute=False,
    ),
)


def test_module_statements_anchor_definition_runs() -> None:
    """Sort definition runs independently without moving anchored statements."""
    source = """def zebra():
    pass


VALUE = 1


def beta():
    pass


def alpha():
    pass


if __name__ == "__main__":
    alpha()
"""
    expected = """def zebra():
    pass


VALUE = 1


def alpha():
    pass


def beta():
    pass


if __name__ == "__main__":
    alpha()
"""
    assert sort_source(source) == expected


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda case: case.name)
def test_scenario_invariants(scenario: _Scenario) -> None:
    """Every permutation compiles, preserves AST content, and sorts idempotently."""
    for arrangement in _arrangements(scenario):
        source = _source(arrangement)
        compile(source, f"<scenario:{scenario.name}:input>", "exec")
        sorted_source = sort_source(source)
        compile(sorted_source, f"<scenario:{scenario.name}:output>", "exec")
        assert _normalised_ast(sorted_source) == _normalised_ast(source), (
            scenario.name,
            arrangement,
        )
        assert sort_source(sorted_source) == sorted_source, (scenario.name, arrangement)


def _arrangements(scenario: _Scenario) -> t.Iterable[tuple[str, ...]]:
    if scenario.permute:
        return itertools.permutations(scenario.blocks)
    return (scenario.blocks,)


def _normalised_ast(source: str) -> str:
    tree = ast.parse(source)

    def normalise_scope(node: ast.Module | ast.ClassDef) -> None:
        node.body = _definition_runs(node.body)
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                normalise_scope(child)

    normalise_scope(tree)
    return ast.dump(tree, include_attributes=False)


def _definition_runs(nodes: list[ast.stmt]) -> list[ast.stmt]:
    """Canonicalise reorderable definition runs without changing nested bodies.

    Returns:
        Nodes with only contiguous definition runs canonicalised.
    """
    result: list[ast.stmt] = []
    run: list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = []

    def flush() -> None:
        # Stable name sorting retains the relative order of duplicate definitions.
        result.extend(sorted(run, key=lambda node: node.name))
        run.clear()

    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            run.append(node)
        else:
            flush()
            result.append(node)
    flush()
    return result


def _source(blocks: tuple[str, ...]) -> str:
    """Join complete definitions and explicitly anchored statements.

    Returns:
        A compilable module assembled from the supplied blocks.
    """
    return "\n\n\n".join(blocks) + "\n"


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            case,
            marks=pytest.mark.xfail(
                reason=case.xfail, strict=True, raises=AssertionError
            ),
        )
        if case.xfail
        else case
        for case in SCENARIOS
    ],
    ids=lambda case: case.name,
)
def test_scenario_order(scenario: _Scenario) -> None:
    """Check full definition order over all safe input permutations."""
    for arrangement in _arrangements(scenario):
        source = _source(arrangement)
        compile(source, f"<scenario:{scenario.name}:input>", "exec")
        actual = _definition_order(sort_source(source))
        assert actual == scenario.expected, (scenario.name, arrangement, actual)


def _definition_order(source: str) -> tuple[str, ...]:
    """Return ordered module and class definition names, retaining duplicates."""
    result: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.append(node.name)
            if isinstance(node, ast.ClassDef):
                result.extend(
                    f"{node.name}.{member.name}"
                    for member in node.body
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
    return tuple(result)
