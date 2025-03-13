import inspect
from inspect import Parameter
from types import LambdaType
from typing import Any, Callable, TypeVar, cast, get_type_hints


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


_T = TypeVar("_T")


def get_return_type(func: Callable[..., _T]) -> type[_T] | None:
    """Get return type of given function if specified or None."""
    return cast(type[_T], get_type_hints(func).get("return"))
