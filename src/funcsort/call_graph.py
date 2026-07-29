"""Extract name references from functions and classes.

Two kinds of reference matter for safe sorting:

- *Definition-time* references: names Python resolves when the ``def``/``class``
  statement itself executes (decorators, base classes, parameter annotations and
  defaults, return annotations, and class-body statements). These are hard
  ordering constraints - a name used here must already be defined.
- *Call-time* references: names used inside function bodies. These only matter at
  call time, so they are a soft preference used to order callees before callers.
"""

import libcst as cst

from .traversal import walk


def call_refs(node: cst.CSTNode) -> set[str]:
    """Return names that are called within a node (bodies included).

    Args:
        node: A ``FunctionDef`` or ``ClassDef`` node.

    Returns:
        The set of called names, e.g. ``foo`` in ``foo()`` and ``bar`` in
        ``self.bar()``. Used as a soft ordering preference (callees before callers).
    """
    names: set[str] = set()
    for call in walk(node):
        if not isinstance(call, cst.Call):
            continue
        func = call.func
        if isinstance(func, cst.Name):
            names.add(func.value)
        elif isinstance(func, cst.Attribute) and isinstance(func.attr, cst.Name):
            names.add(func.attr.value)
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
