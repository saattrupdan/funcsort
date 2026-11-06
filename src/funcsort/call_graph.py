"""Extract name references from functions and classes.

Two kinds of reference matter for safe sorting:

- *Definition-time* references: names Python resolves when the ``def``/``class``
  statement itself executes (decorators, base classes, parameter annotations and
  defaults, return annotations, and class-body statements). These are hard
  ordering constraints - a name used here must already be defined.
- *Call-time* references: names used inside function bodies. These only matter at
  call time, so they are a soft preference used to order callers before callees.
"""

import libcst as cst

from .traversal import field_names, walk


def call_refs(node: cst.CSTNode, enclosing_class: str | None = None) -> set[str]:
    """Return unshadowed call targets used at runtime within a definition.

    Args:
        node: A ``FunctionDef`` or ``ClassDef`` node.
        enclosing_class (optional): Name of the class containing ``node``.

    Returns:
        Called global names and, in a method, same-class ``self``, ``cls`` or
        class-qualified method names. Nested lexical scopes are excluded.
    """
    if isinstance(node, cst.FunctionDef):
        return _function_call_refs(node, enclosing_class=enclosing_class)
    if not isinstance(node, cst.ClassDef):
        return set()

    names: set[str] = set()
    for statement in node.body.body:
        if isinstance(statement, cst.FunctionDef):
            names.update(
                _function_call_refs(
                    statement,
                    enclosing_class=node.name.value,
                    include_method_attributes=False,
                )
            )
        else:
            names.update(_runtime_calls(statement, class_name=node.name.value))
    return names


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
                # Method bodies run at call time; only the signature runs now.
                names |= _signature_names(stmt)
            else:
                names |= collect_names(stmt)
        return names

    return collect_names(node)


def _function_call_refs(
    function: cst.FunctionDef,
    enclosing_class: str | None,
    include_method_attributes: bool = True,
) -> set[str]:
    """Collect calls in one function scope, excluding nested scopes.

    Args:
        function: Function whose runtime body is inspected.
        enclosing_class: Containing class name, or ``None`` for a module function.
        include_method_attributes (optional): Whether to retain class method refs.

    Returns:
        Unshadowed calls relevant to definitions in the current ordering run.
    """
    shadowed = _parameter_names(function.params) | _local_bindings(function.body)
    names = _runtime_calls(
        function.body, class_name=enclosing_class if include_method_attributes else None
    )
    names.difference_update(shadowed)
    return names


def _signature_names(func: cst.FunctionDef) -> set[str]:
    """Return names referenced in a function's decorators and signature.

    Args:
        func: The function definition.

    Returns:
        Names from decorators, parameter annotations/defaults and the return
        annotation - everything evaluated when the ``def`` executes.
    """
    names: set[str] = set()

    for decorator in func.decorators:
        names |= collect_names(decorator.decorator)

    params = func.params
    all_params = [*params.posonly_params, *params.params, *params.kwonly_params]
    star_arg = params.star_arg
    if isinstance(star_arg, cst.Param):
        all_params.append(star_arg)
    if isinstance(params.star_kwarg, cst.Param):
        all_params.append(params.star_kwarg)

    for param in all_params:
        if param.annotation:
            names |= collect_names(param.annotation.annotation)
        if param.default:
            names |= collect_names(param.default)

    if func.returns:
        names |= collect_names(func.returns.annotation)

    return names


def _local_bindings(body: cst.BaseSuite) -> set[str]:
    """Find names bound anywhere in the current function scope.

    Args:
        body: Function body; nested lexical scopes are not traversed.

    Returns:
        Local assignment and import names.
    """
    names: set[str] = set()
    stack = [body]
    while stack:
        current = stack.pop()
        if current is not body and isinstance(current, (cst.FunctionDef, cst.ClassDef)):
            continue
        if isinstance(current, cst.Assign):
            for target in current.targets:
                names.update(_target_names(target.target))
        elif isinstance(current, (cst.AnnAssign, cst.AugAssign)):
            names.update(_target_names(current.target))
        elif isinstance(current, (cst.Import, cst.ImportFrom)):
            names.update(_import_bindings(current))
        for field in field_names(current):
            value = getattr(current, field)
            if isinstance(value, cst.CSTNode):
                stack.append(value)
            elif type(value) is tuple:
                stack.extend(item for item in value if isinstance(item, cst.CSTNode))
    return names


def _parameter_names(params: cst.Parameters) -> set[str]:
    """Return all parameter names in a function signature.

    Args:
        params: Function parameters.

    Returns:
        Names bound when the function is called.
    """
    names = {
        parameter.name.value
        for parameter in (*params.posonly_params, *params.params, *params.kwonly_params)
    }
    if isinstance(params.star_arg, cst.Param):
        names.add(params.star_arg.name.value)
    if isinstance(params.star_kwarg, cst.Param):
        names.add(params.star_kwarg.name.value)
    return names


def _runtime_calls(node: cst.CSTNode, class_name: str | None) -> set[str]:
    """Collect calls without descending into nested function or class scopes.

    Args:
        node: Root of the current runtime scope.
        class_name: Current class name, if the scope is a method or class body.

    Returns:
        Names called directly or passed as bare callback arguments.
    """
    names: set[str] = set()
    stack = [node]
    while stack:
        current = stack.pop()
        if current is not node and isinstance(current, (cst.FunctionDef, cst.ClassDef)):
            continue
        if isinstance(current, cst.Call):
            names.update(_call_targets(current, class_name))
        for field in field_names(current):
            value = getattr(current, field)
            if isinstance(value, cst.CSTNode):
                stack.append(value)
            elif type(value) is tuple:
                stack.extend(item for item in value if isinstance(item, cst.CSTNode))
    return names


def collect_names(node: cst.CSTNode | None) -> set[str]:
    """Collect every ``Name`` value appearing anywhere in a node.

    Args:
        node: The node to scan (or None).

    Returns:
        The set of names referenced. Over-approximates (e.g. attribute names are
        included too), which is safe for dependency detection.
    """
    if node is None:
        return set()

    return {n.value for n in walk(node) if isinstance(n, cst.Name)}


def _call_targets(call: cst.Call, class_name: str | None) -> set[str]:
    """Return the sortable names invoked or passed to a call.

    Args:
        call: Call expression being inspected.
        class_name: Current class name, if this is a method.

    Returns:
        Bare callable names and recognised same-class attribute names.
    """
    names: set[str] = set()
    if isinstance(call.func, cst.Name):
        names.add(call.func.value)
    else:
        attribute = _class_method_attribute(call.func, class_name)
        if attribute is not None:
            names.add(attribute)
    for argument in call.args:
        if isinstance(argument.value, cst.Name):
            names.add(argument.value.value)
        else:
            attribute = _class_method_attribute(argument.value, class_name)
            if attribute is not None:
                names.add(attribute)
    return names


def _import_bindings(statement: cst.Import | cst.ImportFrom) -> set[str]:
    """Return names introduced by an import statement.

    Args:
        statement: Import statement in the current function scope.

    Returns:
        Locally bound imported names.
    """
    aliases = (
        statement.names
        if isinstance(statement, cst.Import)
        else [statement.names]
        if isinstance(statement.names, cst.ImportStar)
        else statement.names
    )
    return {
        alias.asname.name.value
        if isinstance(alias.asname, cst.AsName)
        and isinstance(alias.asname.name, cst.Name)
        else _dotted_name(alias.name).split(".")[0]
        for alias in aliases
        if isinstance(alias, cst.ImportAlias)
    }


def _target_names(target: cst.CSTNode) -> set[str]:
    """Return names bound by an assignment target.

    Args:
        target: Assignment target expression.

    Returns:
        Names bound by the target.
    """
    return {item.value for item in walk(target) if isinstance(item, cst.Name)}


def _class_method_attribute(
    node: cst.BaseExpression, class_name: str | None
) -> str | None:
    """Check whether an attribute is explicitly qualified by this class or self.

    Args:
        node: Function or callback expression.
        class_name: Current class name, or ``None`` outside a method.

    Returns:
        Attribute name when explicitly qualified by this class or self; otherwise
        ``None``.
    """
    if not isinstance(node, cst.Attribute) or not isinstance(node.value, cst.Name):
        return None
    receiver = node.value.value
    if (receiver in {"self", "cls"} and class_name is not None) or (
        receiver == class_name
    ):
        return node.attr.value
    return None


def _dotted_name(node: cst.CSTNode) -> str:
    """Render an import name sufficiently to identify its local binding.

    Args:
        node: Imported dotted name.

    Returns:
        Dotted name, or an empty string for an unexpected expression.
    """
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr.value}" if prefix else node.attr.value
    return ""
