"""Public-interface ordering scenarios with exact expected definition orders."""

import ast
import itertools
import typing as t

import pytest

from funcsort.core import sort_source

# Type alias for a named ordering scenario
_Scenario = tuple[str, dict[str, str], tuple[str, ...]]


SCENARIOS: tuple[_Scenario, ...] = (
    (
        "chain",
        {"leaf": "pass", "middle": "leaf()", "root": "middle()"},
        ("root", "middle", "leaf"),
    ),
    (
        "siblings_breadth_first",
        {"parse": "pass", "load": "parse()", "save": "pass", "main": "load(); save()"},
        ("main", "load", "save", "parse"),
    ),
    (
        "independent_roots",
        {
            "alpha_helper": "pass",
            "alpha": "alpha_helper()",
            "beta_helper": "pass",
            "beta": "beta_helper()",
        },
        ("alpha", "beta", "alpha_helper", "beta_helper"),
    ),
    (
        "shared_helper",
        {
            "shared": "pass",
            "alpha": "shared()",
            "beta": "shared()",
            "main": "alpha(); beta()",
        },
        ("main", "alpha", "beta", "shared"),
    ),
    (
        "diamond",
        {
            "finish": "pass",
            "left": "finish()",
            "right": "finish()",
            "start": "left(); right()",
        },
        ("start", "left", "right", "finish"),
    ),
    (
        "three_levels_sibling_priority",
        {
            "deep": "pass",
            "branch": "deep()",
            "sibling": "pass",
            "root": "branch(); sibling()",
        },
        ("root", "branch", "sibling", "deep"),
    ),
    (
        "alphabetical_roots",
        {"zeta": "pass", "alpha": "pass", "middle": "pass"},
        ("alpha", "middle", "zeta"),
    ),
    ("entry_point", {"helper": "pass", "main": "helper()"}, ("main", "helper")),
    (
        "caller_without_entry",
        {"callee": "pass", "caller": "callee()"},
        ("caller", "callee"),
    ),
    (
        "underscore_helper",
        {"_helper": "pass", "public": "_helper()"},
        ("public", "_helper"),
    ),
    ("mutual_cycle", {"zebra": "alpha()", "alpha": "zebra()"}, ("alpha", "zebra")),
    (
        "three_node_cycle",
        {"gamma": "beta()", "beta": "alpha()", "alpha": "gamma()"},
        ("alpha", "beta", "gamma"),
    ),
    (
        "async_chain",
        {
            "fetch_data": "pass",
            "prepare": "await fetch_data()",
            "main": "await prepare()",
        },
        ("main", "prepare", "fetch_data"),
    ),
    (
        "methods_self_calls",
        {
            "unused": "pass",
            "work": "self.finish()",
            "finish": "pass",
            "__init__": "self.work()",
        },
        ("__init__", "work", "finish", "unused"),
    ),
    (
        "class_method_chain",
        {"z_finish": "pass", "b_work": "self.z_finish()", "a_start": "self.b_work()"},
        ("a_start", "b_work", "z_finish"),
    ),
    (
        "callback_sorted_key",
        {"alpha": "pass", "zebra": "sorted([], key=alpha)"},
        ("zebra", "alpha"),
    ),
    ("callback_map", {"alpha": "pass", "zebra": "map(alpha, [])"}, ("zebra", "alpha")),
    (
        "callback_executor",
        {"alpha": "pass", "zebra": "executor.submit(alpha)"},
        ("zebra", "alpha"),
    ),
    (
        "default_requires_definition",
        {"factory": "pass", "consumer": "def unavailable(): pass"},
        ("consumer", "factory"),
    ),
    (
        "annotation_requires_definition",
        {"Model": "pass", "consumer": "pass"},
        ("Model", "consumer"),
    ),
    ("decorator_dependency", {"decorate": "pass", "use": "pass"}, ("decorate", "use")),
    ("base_before_subclass", {"Child": "pass", "Base": "pass"}, ("Base", "Child")),
    ("metaclass_reference", {"Meta": "pass", "Thing": "pass"}, ("Meta", "Thing")),
    (
        "callee_name_beats_alphabetical",
        {"zebra": "pass", "alpha": "pass", "caller": "zebra()"},
        ("alpha", "caller", "zebra"),
    ),
    (
        "attribute_call",
        {"worker": "pass", "caller": "service.worker()"},
        ("caller", "worker"),
    ),
    (
        "independent_pairs",
        {"zebra": "pass", "alpha": "pass", "beta": "pass", "gamma": "pass"},
        ("alpha", "beta", "gamma", "zebra"),
    ),
    (
        "external_names_ignored",
        {"zebra": "external()", "alpha": "pass"},
        ("alpha", "zebra"),
    ),
    (
        "duplicate_property_names",
        {"first": "pass", "second": "pass"},
        ("first", "second"),
    ),
    (
        "main_chain",
        {"leaf": "pass", "middle": "leaf()", "main": "middle()"},
        ("main", "middle", "leaf"),
    ),
)


_XFAIL_REASONS = {
    "siblings_breadth_first": ("Ordering currently traverses call trees depth-first."),
    "independent_roots": (
        "Root groups currently emit descendants before the next root."
    ),
    "shared_helper": (
        "Shared callees emit during the first root's depth-first traversal."
    ),
    "diamond": ("Shared callees emit during the first branch's depth-first traversal."),
    "three_node_cycle": (
        "Cycles currently preserve traversal order, not alphabetical order."
    ),
    "three_levels_sibling_priority": (
        "Ordering currently traverses call trees depth-first."
    ),
    "callback_sorted_key": "Callback names are not ordering dependencies yet.",
    "callback_map": "Callback names are not ordering dependencies yet.",
    "callback_executor": "Callback names are not ordering dependencies yet.",
}


def test_module_statements_anchor_definition_runs() -> None:
    """Sort definition runs independently without moving anchored assignments."""
    source = """def zebra():
    pass


VALUE = 1


def beta():
    pass


def alpha():
    pass
"""
    expected = """def zebra():
    pass


VALUE = 1


def alpha():
    pass


def beta():
    pass
"""
    assert sort_source(source) == expected


@pytest.mark.parametrize(
    ("scenario_name", "definitions", "expected"),
    SCENARIOS,
    ids=[case[0] for case in SCENARIOS],
)
def test_scenario_is_idempotent_and_preserves_definitions(
    scenario_name: str, definitions: dict[str, str], expected: tuple[str, ...]
) -> None:
    """Check sorting is stable and does not lose or alter definition bodies."""
    source = _source(definitions, expected)
    sorted_source = sort_source(source)
    assert sort_source(sorted_source) == sorted_source
    before = sorted(ast.dump(node) for node in ast.parse(source).body)
    after = sorted(ast.dump(node) for node in ast.parse(sorted_source).body)
    assert after == before


def _source(definitions: dict[str, str], order: t.Iterable[str]) -> str:
    """Build a source module in the requested definition order.

    Args:
        definitions: Function bodies indexed by definition name.
        order: Names to emit in source order.

    Returns:
        A source module containing the requested definitions.
    """
    blocks = []
    for name in order:
        body = definitions[name]
        blocks.append(f"def {name}():\n    {body}")
    return "\n\n\n".join(blocks) + "\n"


ORDERING_CASES = tuple(
    pytest.param(
        *case,
        marks=pytest.mark.xfail(reason=_XFAIL_REASONS[case[0]], raises=AssertionError),
    )
    if case[0] in _XFAIL_REASONS
    else pytest.param(*case)
    for case in SCENARIOS
)


@pytest.mark.parametrize(
    ("scenario_name", "definitions", "expected"),
    ORDERING_CASES,
    ids=[case[0] for case in SCENARIOS],
)
def test_scenario_order(
    scenario_name: str, definitions: dict[str, str], expected: tuple[str, ...]
) -> None:
    """Check named ordering scenarios through the public source interface."""
    for input_order in _bounded_orders(tuple(definitions)):
        source = _source(definitions, input_order)
        assert _ordered_names(sort_source(source)) == expected, scenario_name


def _bounded_orders(names: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Return exhaustive permutations for small scenarios and deterministic samples."""
    if len(names) <= 4:
        return list(itertools.permutations(names))
    return [names, tuple(reversed(names)), tuple(sorted(names))]


def _ordered_names(source: str) -> tuple[str, ...]:
    """Return top-level function names in source order."""
    return tuple(
        node.name
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
