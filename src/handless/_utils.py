from __future__ import annotations

import inspect
from contextlib import AbstractContextManager, contextmanager
from inspect import Parameter, isgeneratorfunction
from typing import (
    TYPE_CHECKING,
    Any,
    NewType,
    ParamSpec,
    TypeVar,
    cast,
    get_type_hints,
    overload,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_T = TypeVar("_T")


def get_untyped_parameters(params: dict[str, Parameter]) -> list[str]:
    """List keys of given dict having `Parameter.empty` value."""
    return [
        pname for pname, param in params.items() if param.annotation is Parameter.empty
    ]


def get_first_param_name(func: Callable[..., Any]) -> str:
    """Get the name of the first parameter of given function, if any, otherwise raise an error."""
    try:
        return next(iter(inspect.signature(func).parameters))
    except StopIteration:
        msg = "Given function has no parameters"
        raise ValueError(msg) from None


def get_return_type(func: Callable[..., _T]) -> type[_T] | None:
    """Get return type of given function if specified or None."""
    return cast("type[_T]", get_type_hints(func).get("return"))


def get_non_variadic_params(callable_: Callable[..., Any]) -> dict[str, Parameter]:
    """Return non variadic parameters of given callable mapped to their name.

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


def compare_functions(a: Callable[..., Any], b: Callable[..., Any]) -> bool:
    """Check if the two given functions are identicals.

    Return true even if both functions are not refering the same object in memory.
    The funnction will try to compare the function compiled code itself if possible.
    """
    a_code = a.__code__.co_code if hasattr(a, "__code__") else a
    b_code = b.__code__.co_code if hasattr(b, "__code__") else b
    return a_code == b_code


_P = ParamSpec("_P")


@overload
def autocontextmanager(
    factory: Callable[_P, Iterator[_T]],
) -> Callable[_P, AbstractContextManager[_T]]: ...


@overload
def autocontextmanager(factory: Callable[_P, _T]) -> Callable[_P, _T]: ...


def autocontextmanager(factory: Callable[..., Any]) -> Callable[..., Any]:
    if inspect.isgeneratorfunction(factory):
        return contextmanager(factory)
    return factory


def get_injectable_params(
    function: Callable[..., Any], *, overrides: dict[str, type[Any]] | None = None
) -> tuple[inspect.Parameter, ...]:
    # Merge given callable inspected params with provided ones.
    # NOTE: we omit variadic params because we don't know how to autowire them yet
    params = get_non_variadic_params(function)
    for pname, override_type in (overrides or {}).items():
        params[pname] = params[pname].replace(annotation=override_type)

    if empty_params := get_untyped_parameters(params):
        # NOTE: if some parameters are missing type annotation we cannot autowire
        msg = f"Factory {function} is missing types for following parameters: {', '.join(empty_params)}"
        raise TypeError(msg)

    return tuple(params.values())


def iscontextmanager(function: Callable[..., Any]) -> bool:
    return hasattr(function, "__wrapped__") and isgeneratorfunction(
        function.__wrapped__
    )
