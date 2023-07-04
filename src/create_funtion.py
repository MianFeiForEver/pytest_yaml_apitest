from inspect import Parameter, Signature
from typing import Any, Callable, Mapping, Sequence


def create_function_from_parameters(
    func: Callable[[Mapping[str, Any]], Any],
    parameters: Sequence[Parameter],
    documentation=None,
    func_name=None,
):
    new_signature = Signature(parameters)

    def modified_func(**kwargs):
        return func(kwargs)

    modified_func.__doc__ = documentation
    modified_func.__signature__ = new_signature
    modified_func.__name__ = func_name
    return modified_func
