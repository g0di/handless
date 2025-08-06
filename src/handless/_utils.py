from __future__ import annotations

import inspect
from functools import cache
from inspect import Parameter, isgeneratorfunction
from typing import TYPE_CHECKING, Any, NewType, TypeVar, cast, get_type_hints
from unittest.mock import Mock

if TYPE_CHECKING:
    from collections.abc import Callable

_T = TypeVar("_T")


@cache
def get_return_type(func: Callable[..., _T]) -> type[_T] | None:
    """Get return type of given function if specified or None."""
    return cast("type[_T]", get_type_hints(func).get("return"))


@cache
def get_non_variadic_params(callable_: Callable[..., Any]) -> dict[str, Parameter]:
    """Return non variadic parameters of given callable mapped to their name.

    Non variadic parameters are all parameters except *args and **kwargs
    """
    # NOTE: when receiving a mock or a new type we must inspect the signature of the
    # wrapped object because inspect does not do it automatically
    callable_to_inspect = (
        callable_.__supertype__
        if isinstance(callable_, NewType)
        else callable_._mock_wraps  # noqa: SLF001
        if isinstance(callable_, Mock)
        else callable_
    )
    signature = inspect.signature(callable_to_inspect, eval_str=True)
    return {
        name: param
        for name, param in signature.parameters.items()
        if param.kind not in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}
    }


def are_functions_equal(a: Callable[..., Any], b: Callable[..., Any]) -> bool:
    """Check if the two given functions are identicals.

    Return true even if both functions are not refering the same object in memory.
    The function will try to compare the function compiled code itself if possible.
    """
    a_code = a.__code__.co_code if hasattr(a, "__code__") else a
    b_code = b.__code__.co_code if hasattr(b, "__code__") else b
    return a_code == b_code


def iscontextmanager(function: Callable[..., Any]) -> bool:
    return hasattr(function, "__wrapped__") and isgeneratorfunction(
        function.__wrapped__
    )
