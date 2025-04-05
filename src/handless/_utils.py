import inspect
from inspect import Parameter
from types import LambdaType
from typing import Any, Callable, NewType, TypeVar, cast, get_type_hints

_T = TypeVar("_T")


def count_func_params(value: Callable[..., Any]) -> int:
    """Return the total number of parameters of given function."""
    return len(inspect.signature(value).parameters)


def get_untyped_parameters(params: dict[str, Parameter]) -> list[str]:
    """List keys of given dict having `Parameter.empty` value."""
    return [
        pname for pname, param in params.items() if param.annotation is Parameter.empty
    ]


def is_lambda_function(value: Any) -> bool:
    """Returns true if given function is a lambda."""
    return isinstance(value, LambdaType) and value.__name__ == "<lambda>"


def get_return_type(func: Callable[..., _T]) -> type[_T] | None:
    """Get return type of given function if specified or None."""
    return cast(type[_T], get_type_hints(func).get("return"))


def get_non_variadic_params(callable_: Callable[..., Any]) -> dict[str, Parameter]:
    """Returns a dict mapping given callable non variadic parameters name to their type.

    Non variadic parameters are all parameters except *args and **kwargs
    """
    signature = inspect.signature(
        callable_.__supertype__ if isinstance(callable_, NewType) else callable_,
        eval_str=True,
    )
    return {
        name: param
        for name, param in signature.parameters.items()
        if param.kind not in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}
    }


def default(value: _T | None, default_value: _T) -> _T:
    """Return default value if given value is None."""
    return default_value if value is None else value
