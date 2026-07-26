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
    """Build a dependency graph for a list of sortable units.

    Creates edges from a unit to its dependencies (function calls, decorator usages,
    and type hint references).

    Args:
        units: List of sortable units in scope.

    Returns:
        Dict mapping unit name to set of units it depends on.
    """
    unit_names = {unit.name for unit in units}
    graph: dict[str, set[str]] = {}

    for unit in units:
        deps: set[str] = set()
        if isinstance(unit.node, cst.FunctionDef):
            calls = extract_calls(unit.node)
            decorators = extract_decorators(unit.node)
            type_refs = extract_type_annotations(unit.node)
            deps = calls | decorators | type_refs
        elif isinstance(unit.node, cst.ClassDef):
            # Classes can depend on base classes and type hints in class body
            base_refs = extract_class_bases(unit.node)
            body_refs = extract_class_body_type_refs(unit.node)
            deps = base_refs | body_refs
        elif isinstance(unit.node, cst.AnnAssign):
            # Constants with type annotations depend on the types
            if unit.node.annotation:
                type_refs = _extract_names_from_annotation(unit.node.annotation.annotation)
                deps = type_refs
            if unit.node.value:
                value_refs = _extract_names_from_assign_value(unit.node.value)
                deps = deps | value_refs
        elif isinstance(unit.node, cst.Assign):
            # Constants with assignments depend on any calls in the value
            value_refs = _extract_names_from_assign_value(unit.node.value)
            deps = value_refs
        # Filter to only sibling units
        graph[unit.name] = deps & unit_names

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


def extract_type_annotations(func_node: cst.FunctionDef) -> set[str]:
    """Extract class/type references from function type annotations.

    Extracts bare Name nodes from parameter annotations and return type.

    Args:
        func_node: The function definition node.

    Returns:
        Set of type/class names referenced in annotations.
    """
    refs: set[str] = set()

    # Extract from parameters (annotation.annotation is the actual type)
    for param in func_node.params.params:
        if param.annotation:
            refs.update(_extract_names_from_annotation(param.annotation.annotation))

    # Extract from return type
    if func_node.returns:
        refs.update(_extract_names_from_annotation(func_node.returns.annotation))

    return refs


def _extract_names_from_annotation(annotation: cst.BaseExpression) -> set[str]:
    """Extract bare Name references from a type annotation.

    Handles Name, Subscript (e.g., list[T]), and other common patterns.
    """
    refs: set[str] = set()

    if m.matches(annotation, m.Name()):
        assert isinstance(annotation, cst.Name)
        refs.add(annotation.value)
    elif m.matches(annotation, m.Subscript()):
        assert isinstance(annotation, cst.Subscript)
        # For list[T], dict[K, V], etc. - extract the base and args
        if m.matches(annotation.value, m.Name()):
            assert isinstance(annotation.value, cst.Name)
            refs.add(annotation.value.value)
        for item in annotation.slice:
            # Unwrap Index if present (libcst wraps subscript elements in Index)
            slice_node = item.slice
            if isinstance(slice_node, cst.Index):
                slice_node = slice_node.value
            if isinstance(slice_node, cst.Name):
                refs.add(slice_node.value)
            elif m.matches(slice_node, m.Subscript()):
                assert isinstance(slice_node, cst.Subscript)
                refs.update(_extract_names_from_annotation(slice_node))

    return refs


def extract_class_bases(class_node: cst.ClassDef) -> set[str]:
    """Extract base class references from a class definition.

    Args:
        class_node: The class definition node.

    Returns:
        Set of base class names.
    """
    refs: set[str] = set()
    for base in class_node.bases:
        if m.matches(base.value, m.Name()):
            assert isinstance(base.value, cst.Name)
            refs.add(base.value.value)
    return refs


def _extract_names_from_assign_value(value: cst.BaseExpression) -> set[str]:
    """Extract class names referenced in an assignment value.

    Handles Call nodes (e.g., `DummyDevice()`) and other expressions.

    Args:
        value: The assignment value expression.

    Returns:
        Set of class/type names referenced.
    """
    refs: set[str] = set()

    # Handle function/method calls like `DummyDevice()`
    if m.matches(value, m.Call()):
        assert isinstance(value, cst.Call)
        func = value.func
        # Extract bare function name
        if m.matches(func, m.Name()):
            assert isinstance(func, cst.Name)
            refs.add(func.value)
        # Extract method calls like `self.method()` - just the method name
        elif m.matches(func, m.Attribute()):
            assert isinstance(func, cst.Attribute)
            if isinstance(func.attr, cst.Name):
                refs.add(func.attr.value)

    return refs


def extract_class_body_type_refs(class_node: cst.ClassDef) -> set[str]:
    """Extract type references from class body annotations and assignments.

    Extracts bare Name nodes from:
    - Annotated assignments in the class body (e.g., `item: Item`)
    - Regular assignments where value is a class call (e.g., `device = DummyDevice()`)

    Args:
        class_node: The class definition node.

    Returns:
        Set of type/class names referenced in class body.
    """
    refs: set[str] = set()

    for stmt in class_node.body.body:
        # Statements are wrapped in SimpleStatementLine
        if m.matches(stmt, m.SimpleStatementLine()):
            assert isinstance(stmt, cst.SimpleStatementLine)
            for inner_stmt in stmt.body:
                # Handle annotated assignments like `item: Item`
                if m.matches(inner_stmt, m.AnnAssign()):
                    assert isinstance(inner_stmt, cst.AnnAssign)
                    annotation = inner_stmt.annotation
                    if annotation:
                        refs.update(_extract_names_from_annotation(annotation.annotation))
                # Handle regular assignments like `device = DummyDevice()`
                elif m.matches(inner_stmt, m.Assign()):
                    assert isinstance(inner_stmt, cst.Assign)
                    refs.update(_extract_names_from_assign_value(inner_stmt.value))

    return refs
