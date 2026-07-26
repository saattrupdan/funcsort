"""Extract call graphs from function bodies."""

import libcst as cst
import libcst.matchers as m

from .models import SortableUnit


class _CallCollector(cst.CSTVisitor):
    """Collect all function/method names and name references within a function body.

    Ignores nested function definitions. Collects:
    - Bare function calls (foo())
    - Method calls (self.foo())
    - Bare name references that could refer to siblings (e.g., CONSTANT)
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
        elif m.matches(original_node, m.Name()) and isinstance(original_node, cst.Name):
            # Also collect bare name references (e.g., CONSTANT in print(CONSTANT))
            # Skip builtins and common locals
            name = original_node.value
            if name not in ("None", "True", "False", "self", "cls"):
                self.calls.add(name)


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
        # Filter to only sibling units (exclude self-references)
        graph[unit.name] = (deps & unit_names) - {unit.name}

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
    """Extract class/type references from function type annotations and defaults.

    Extracts bare Name nodes from:
    - Parameter annotations
    - Return type annotation
    - Default values (including lambdas)

    Args:
        func_node: The function definition node.

    Returns:
        Set of type/class names referenced in annotations and defaults.
    """
    refs: set[str] = set()

    # Extract from parameters (annotation and default values)
    for param in func_node.params.params:
        if param.annotation:
            refs.update(_extract_names_from_annotation(param.annotation.annotation))
        if param.default:
            refs.update(_extract_names_from_expression(param.default))

    # Handle *args (star_arg) if present
    if func_node.params.star_arg and not isinstance(
        func_node.params.star_arg, cst.MaybeSentinel
    ):
        if func_node.params.star_arg.annotation:
            refs.update(
                _extract_names_from_annotation(func_node.params.star_arg.annotation.annotation)
            )

    # Handle **kwargs (star_kwarg) if present
    if func_node.params.star_kwarg and not isinstance(
        func_node.params.star_kwarg, cst.MaybeSentinel
    ):
        if func_node.params.star_kwarg.annotation:
            refs.update(
                _extract_names_from_annotation(func_node.params.star_kwarg.annotation.annotation)
            )

    # Extract from return type
    if func_node.returns:
        refs.update(_extract_names_from_annotation(func_node.returns.annotation))

    return refs


def _extract_names_from_annotation(annotation: cst.BaseExpression) -> set[str]:
    """Extract bare Name references from a type annotation.

    Handles:
    - Name (e.g., Item)
    - Subscript (e.g., list[T], dict[K, V])
    - BinaryOperation with BitOr (e.g., Input | Config for Union types)
    - Attribute (e.g., module.Class)

    Args:
        annotation: The annotation expression.

    Returns:
        Set of type/class names referenced.
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
    elif m.matches(annotation, m.BinaryOperation()):
        # Handle Union types: Input | Config
        assert isinstance(annotation, cst.BinaryOperation)
        if m.matches(annotation.operator, m.BitOr()):
            refs.update(_extract_names_from_annotation(annotation.left))
            refs.update(_extract_names_from_annotation(annotation.right))
    elif m.matches(annotation, m.Attribute()):
        # Handle module.Class - extract just the class name
        assert isinstance(annotation, cst.Attribute)
        if isinstance(annotation.attr, cst.Name):
            refs.add(annotation.attr.value)

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


def _extract_names_from_expression(expr: cst.BaseExpression) -> set[str]:
    """Extract all function/class names referenced in an expression.

    Walks the expression tree to find:
    - Function calls (bare and method calls)
    - Bare name references (e.g., type hints, variables)
    - Names inside lambdas

    Args:
        expr: The expression to walk.

    Returns:
        Set of function/class names referenced.
    """
    refs: set[str] = set()

    class _NameVisitor(cst.CSTVisitor):
        def __init__(self) -> None:
            self.names: set[str] = set()

        def on_visit(self, node: cst.CSTNode) -> bool:
            if m.matches(node, m.Call()):
                assert isinstance(node, cst.Call)
                func = node.func
                # Extract bare function calls
                if m.matches(func, m.Name()):
                    assert isinstance(func, cst.Name)
                    self.names.add(func.value)
                # Extract method calls like self.method()
                elif m.matches(func, m.Attribute()):
                    assert isinstance(func, cst.Attribute)
                    if isinstance(func.attr, cst.Name):
                        self.names.add(func.attr.value)
            elif m.matches(node, m.Name()):
                # Extract bare names (e.g., type hints, variables, classes)
                # But skip common builtins
                assert isinstance(node, cst.Name)
                if node.value not in ("None", "True", "False", "self", "cls"):
                    self.names.add(node.value)
            # Lambda bodies can contain calls/refs
            return True

    visitor = _NameVisitor()
    expr.visit(visitor)
    return visitor.names


def _extract_names_from_assign_value(value: cst.BaseExpression) -> set[str]:
    """Extract function/class names referenced in an assignment value.

    Alias for _extract_names_from_expression for backwards compatibility.
    """
    return _extract_names_from_expression(value)


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
