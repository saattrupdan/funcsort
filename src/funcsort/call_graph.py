"""Extract call graphs from function bodies."""

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit


class _CallCollector(cst.CSTVisitor):
    """Collect all function/method names called within a function body.

    Ignores nested function definitions and method calls on objects (only
    collects bare names that could refer to sibling functions).
    """

    def __init__(self) -> None:
        self.calls: set[str] = set()
        self._depth: int = 0

    def on_visit(self, node: cst.CSTNode) -> bool:
        if m.matches(node, m.FunctionDef()):
            # Only visit body of top-level function (depth 0)
            # Nested functions (depth > 0) should be skipped
            if self._depth > 0:
                return False
            self._depth += 1
        return True

    def on_leave(self, original_node: cst.CSTNode) -> None:
        if m.matches(original_node, m.FunctionDef()):
            self._depth -= 1
        if m.matches(original_node, m.Call()) and isinstance(original_node, cst.Call):
            func = original_node.func
            # Handle both bare function calls and method calls (self.foo())
            if m.matches(func, m.Name()) and isinstance(func, cst.Name):
                self.calls.add(func.value)
            elif m.matches(func, m.Attribute()) and isinstance(func, cst.Attribute):
                # For self.method(), extract just 'method'
                if isinstance(func.attr, cst.Name):
                    self.calls.add(func.attr.value)


def build_call_graph(units: list[SortableUnit]) -> dict[str, set[str]]:
    """Build a call graph for a list of sortable units.

    Creates edges from caller to callee for same-scope function calls and
    decorator usages.

    Args:
        units: List of sortable units in scope.

    Returns:
        Dict mapping function name to set of functions it depends on.
    """
    unit_names = {unit.name for unit in units}
    graph: dict[str, set[str]] = {}

    for unit in units:
        calls = extract_calls(unit.node)
        decorators = extract_decorators(unit.node)
        # Filter to only sibling functions
        graph[unit.name] = (calls | decorators) & unit_names

    return graph


def extract_decorators(func_node: cst.FunctionDef) -> set[str]:
    """Extract all decorator names from a function definition.

    Only extracts bare Name decorators (e.g. @my_decorator), not
    complex expressions (e.g. @decorator_factory()).

    Args:
        func_node: The function definition node.

    Returns:
        Set of decorator names.
    """
    decorators: set[str] = set()
    for decorator in func_node.decorators:
        if m.matches(decorator.decorator, m.Name()):
            name = decorator.decorator
            assert isinstance(name, cst.Name)
            decorators.add(name.value)
    return decorators


def extract_calls(func_node: cst.FunctionDef) -> set[str]:
    """Extract all function calls from a function body.

    Args:
        func_node: The function definition node.

    Returns:
        Set of function names called within the function.
    """
    collector = _CallCollector()
    func_node.visit(collector)
    return collector.calls
