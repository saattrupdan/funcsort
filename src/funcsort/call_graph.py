"""Extract definition-time dependencies and scope-resolved runtime references."""

import collections.abc as c

import libcst as cst
from libcst.metadata import (
    Assignment,
    BuiltinScope,
    ComprehensionScope,
    GlobalScope,
    MetadataWrapper,
    Scope,
    ScopeProvider,
)

from .traversal import field_names, walk


def call_refs(
    nodes: c.Sequence[cst.FunctionDef | cst.ClassDef],
    enclosing_class: str | None = None,
) -> list[set[str]]:
    """Resolve runtime dependencies for a run of definitions together.

    Args:
        nodes: Function and class definitions in their original order.
        enclosing_class (optional): Containing class for a method-ordering run.

    Returns:
        One set per definition: global names for a module run, or qualified method
        names for a class run. Bare callbacks use Python's lexical scope rules.
    """
    wrapper = MetadataWrapper(cst.Module(body=tuple(nodes)))
    scopes = wrapper.resolve(ScopeProvider)
    local_bindings = _missing_local_bindings(wrapper.module, scopes)
    return [
        _definition_refs(definition, scopes, local_bindings, enclosing_class)
        for definition in wrapper.module.body
    ]


def def_time_refs(node: cst.CSTNode) -> set[str]:
    """Return names a function/class definition resolves at definition time.

    Args:
        node: A ``FunctionDef`` or ``ClassDef`` node.

    Returns:
        Names referenced in decorators, signatures, base classes and class-body
        statements (but not inside method bodies).
    """
    if isinstance(node, cst.FunctionDef):
        return _signature_names(node)

    if isinstance(node, cst.ClassDef):
        names: set[str] = set()
        for decorator in node.decorators:
            names |= collect_names(decorator.decorator)
        for base in node.bases:
            names |= collect_names(base.value)
        for keyword in node.keywords:
            names |= collect_names(keyword.value)
        for stmt in node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                names |= _signature_names(stmt)
            else:
                names |= collect_names(stmt)
        return names

    return collect_names(node)


def _definition_refs(
    definition: cst.BaseStatement,
    scopes: c.Mapping[cst.CSTNode, Scope],
    local_bindings: c.Mapping[Scope, frozenset[str]],
    enclosing_class: str | None,
) -> set[str]:
    """Extract runtime edges from one definition using shared lexical metadata.

    Args:
        definition: Definition in a module or method run.
        scopes: Lexical scope metadata resolved once for the entire run.
        local_bindings: Pattern and comprehension bindings missing from LibCST metadata.
        enclosing_class: Containing class for a method run, or ``None``.

    Returns:
        Names that can refer to other definitions in the same ordering run.
    """
    if isinstance(definition, cst.FunctionDef):
        receiver = _method_receiver(definition) if enclosing_class else None
        return _runtime_refs(
            definition.body,
            scopes,
            local_bindings,
            class_name=enclosing_class,
            receiver=receiver,
        )

    if not isinstance(definition, cst.ClassDef):
        return set()
    names: set[str] = set()
    for statement in definition.body.body:
        # Method bodies contribute globals to the class's module-level edges,
        # never sibling-method names which happen to match a global definition.
        runtime = (
            statement.body if isinstance(statement, cst.FunctionDef) else statement
        )
        names.update(_runtime_refs(runtime, scopes, local_bindings))
    return names


def _missing_local_bindings(
    module: cst.Module, scopes: c.Mapping[cst.CSTNode, Scope]
) -> dict[Scope, frozenset[str]]:
    """Supplement scope metadata for pattern captures and comprehension walruses.

    Args:
        module: Module whose references are being resolved.
        scopes: LibCST lexical scopes for the module.

    Returns:
        Names omitted by ScopeProvider, keyed by their owning lexical scope.
    """
    bindings: dict[Scope, set[str]] = {}
    for node in walk(module):
        capture: cst.Name | None = None
        if isinstance(node, (cst.MatchAs, cst.MatchStar)):
            capture = node.name if isinstance(node.name, cst.Name) else None
        elif isinstance(node, cst.MatchMapping):
            capture = node.rest if isinstance(node.rest, cst.Name) else None
        if capture is not None:
            owner = scopes.get(node)
            if owner is not None:
                bindings.setdefault(owner, set()).add(capture.value)
        elif isinstance(node, cst.NamedExpr):
            owner = scopes.get(node.target)
            if isinstance(owner, ComprehensionScope) and isinstance(
                node.target, cst.Name
            ):
                while isinstance(owner, ComprehensionScope):
                    owner = owner.parent
                if owner is not None:
                    bindings.setdefault(owner, set()).add(node.target.value)
    return {scope: frozenset(names) for scope, names in bindings.items()}


def _signature_names(func: cst.FunctionDef) -> set[str]:
    """Return names referenced in a function's decorators and signature.

    Args:
        func: Function definition whose signature is inspected.

    Returns:
        Names evaluated when the function definition executes.
    """
    names: set[str] = set()
    for decorator in func.decorators:
        names |= collect_names(decorator.decorator)

    params = func.params
    all_params = [*params.posonly_params, *params.params, *params.kwonly_params]
    if isinstance(params.star_arg, cst.Param):
        all_params.append(params.star_arg)
    if params.star_kwarg:
        all_params.append(params.star_kwarg)
    for param in all_params:
        if param.annotation:
            names |= collect_names(param.annotation.annotation)
        if param.default:
            names |= collect_names(param.default)
    if func.returns:
        names |= collect_names(func.returns.annotation)
    return names


def _method_receiver(function: cst.FunctionDef) -> cst.Param | None:
    """Identify the conventional instance or class parameter of a method.

    Args:
        function: Method definition whose body is inspected.

    Returns:
        Its first parameter when named ``self`` or ``cls``, except for static methods.
    """
    if any(
        isinstance(decorator.decorator, cst.Name)
        and decorator.decorator.value == "staticmethod"
        for decorator in function.decorators
    ):
        return None
    positional = (*function.params.posonly_params, *function.params.params)
    if positional and positional[0].name.value in {"self", "cls"}:
        return positional[0]
    return None


def _runtime_refs(
    node: cst.CSTNode,
    scopes: c.Mapping[cst.CSTNode, Scope],
    local_bindings: c.Mapping[Scope, frozenset[str]],
    class_name: str | None = None,
    receiver: cst.Param | None = None,
) -> set[str]:
    """Collect resolved call targets in one runtime body.

    Args:
        node: Body or statement evaluated in the current scope.
        scopes: LibCST's lexical scope metadata for the enclosing definition.
        local_bindings: Pattern and comprehension bindings missing from LibCST metadata.
        class_name (optional): Class whose qualified methods are being ordered.
        receiver (optional): Instance or class parameter of the current method.

    Returns:
        Names matching the current module or method ordering run.
    """
    names: set[str] = set()
    for current in _runtime_nodes(node):
        if not isinstance(current, cst.Call):
            continue
        expressions = [current.func, *(argument.value for argument in current.args)]
        for expression in expressions:
            if class_name is None:
                if isinstance(expression, cst.Name) and _is_global(
                    expression, scopes, local_bindings
                ):
                    names.add(expression.value)
            elif (
                isinstance(expression, cst.Attribute)
                and isinstance(expression.value, cst.Name)
                and _is_method_receiver(
                    expression.value, scopes, local_bindings, class_name, receiver
                )
            ):
                names.add(expression.attr.value)
    return names


def collect_names(node: cst.CSTNode | None) -> set[str]:
    """Collect every ``Name`` value appearing anywhere in a node.

    Args:
        node: Node to scan, or ``None``.

    Returns:
        Referenced names, including attribute names for conservative safety.
    """
    if node is None:
        return set()
    return {item.value for item in walk(node) if isinstance(item, cst.Name)}


def _is_method_receiver(
    name: cst.Name,
    scopes: c.Mapping[cst.CSTNode, Scope],
    local_bindings: c.Mapping[Scope, frozenset[str]],
    class_name: str,
    receiver: cst.Param | None,
) -> bool:
    """Resolve a recognised class or instance receiver without guessing its type.

    Args:
        name: Receiver of a qualified call or callback expression.
        scopes: Lexical scope metadata for the enclosing definition.
        local_bindings: Pattern and comprehension bindings missing from LibCST metadata.
        class_name: Class whose methods are being sorted.
        receiver: Method's instance or class parameter, if present.

    Returns:
        Whether the expression refers to this class or its method receiver.
    """
    if name.value == class_name:
        return _is_global(name, scopes, local_bindings)
    if receiver is None or name.value != receiver.name.value:
        return False
    scope = scopes.get(name)
    if scope is None:
        return False
    assignments = scope[name.value]
    return bool(assignments) and all(
        isinstance(assignment, Assignment)
        and assignment.node is receiver
        and name.value not in local_bindings.get(assignment.scope, frozenset())
        for assignment in assignments
    )


def _runtime_nodes(node: cst.CSTNode) -> c.Iterator[cst.CSTNode]:
    """Walk runtime expressions without entering nested callable bodies.

    Args:
        node: Root of a runtime body or statement.

    Yields:
        Nodes evaluated by that scope, including nested definition signatures.
    """
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, (cst.FunctionDef, cst.Lambda)):
            stack.append(current.params)
            if isinstance(current, cst.FunctionDef):
                stack.extend(current.decorators)
                if current.returns is not None:
                    stack.append(current.returns)
            continue
        yield current
        for field in field_names(current):
            value = getattr(current, field)
            if isinstance(value, cst.CSTNode):
                stack.append(value)
            elif type(value) is tuple:
                stack.extend(item for item in value if isinstance(item, cst.CSTNode))


def _is_global(
    name: cst.Name,
    scopes: c.Mapping[cst.CSTNode, Scope],
    local_bindings: c.Mapping[Scope, frozenset[str]],
) -> bool:
    """Check that a bare name is not bound in a local lexical scope.

    Args:
        name: Name expression being resolved.
        scopes: Lexical scope metadata for the enclosing definition.
        local_bindings: Pattern and comprehension bindings missing from LibCST metadata.

    Returns:
        Whether resolution can refer to a module-level definition.
    """
    scope = scopes.get(name)
    if scope is None:
        return False
    current: Scope | None = scope
    while current is not None and not isinstance(current, GlobalScope):
        if name.value in local_bindings.get(current, frozenset()):
            overwritten_scope = getattr(current, "_scope_overwrites", {})
            if name.value not in overwritten_scope:
                return False
        current = current.parent
    # The wrapper contains one definition, so unresolved/builtin names may refer
    # to another definition in the caller's module run.
    return all(
        isinstance(assignment.scope, (GlobalScope, BuiltinScope))
        for assignment in scope[name.value]
    )
