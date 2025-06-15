from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from inspect import Parameter, isgeneratorfunction
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeGuard, TypeVar, overload

from handless._utils import (
    compare_functions,
    get_non_variadic_params,
    get_untyped_parameters,
)
from handless.lifetimes import Singleton, Transient

if TYPE_CHECKING:
    from collections.abc import Iterator
    from contextlib import AbstractContextManager

    from handless._registry import Registry
    from handless.container import Scope
    from handless.lifetimes import Lifetime

_T = TypeVar("_T")
Provider = Callable[["Scope"], _T]
Factory = Provider[_T] | Callable[[], _T]


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: Provider[_T | AbstractContextManager[_T]]
    enter: bool
    lifetime: Lifetime

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Binding)
            and self.type_ == value.type_
            and compare_functions(self.provider, value.provider)
            and self.enter == value.enter
            and self.lifetime == value.lifetime
        )


class Binder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def alias(self, alias_type: type[_T]) -> None:
        """Resolve the given type when resolving the registered one."""
        self.factory(lambda c: c.resolve(alias_type), lifetime=Transient(), enter=False)

    @overload
    def value(self, value: _T, *, enter: bool = ...) -> None: ...

    # NOTE: following overload ensure enter is True when passing a context manager not being
    # an instance of _T
    @overload
    def value(
        self, value: AbstractContextManager[_T], *, enter: Literal[True]
    ) -> None: ...

    def value(self, value: Any, *, enter: bool = False) -> None:
        """Use given value when resolving the registered type."""
        self.factory(lambda _: value, lifetime=Singleton(), enter=enter)

    @overload
    def factory(
        self,
        factory: Factory[_T],
        *,
        lifetime: Lifetime | None = ...,
        enter: bool = ...,
    ) -> None: ...

    # NOTE:: Following overload ensure enter must not be False when passing a callable returning
    # context manager or an iterator not being an instance of _T
    @overload
    def factory(
        self,
        factory: Factory[Iterator[_T] | AbstractContextManager[_T]],
        *,
        lifetime: Lifetime | None = ...,
        enter: Literal[True] = ...,
    ) -> None: ...

    def factory(
        self,
        factory: Factory[Any],
        *,
        lifetime: Lifetime | None = None,
        enter: bool = True,
    ) -> None:
        """Use a function to produce an instance of registered type when resolved.

        The function can eventually takes a single argument allowing to resolve nested
        dependencies required to build this type.
        """
        if isgeneratorfunction(factory):
            factory = contextmanager(factory)

        if _is_factory_a_provider(factory):
            self._provider(factory, lifetime=lifetime, enter=enter)
        else:
            # If the given function is not taking any argument
            self._provider(lambda _: factory(), lifetime=lifetime, enter=enter)  # type: ignore[call-arg]

    def _provider(
        self,
        provider: Provider[_T],
        *,
        lifetime: Lifetime | None = None,
        enter: bool = True,
    ) -> None:
        binding = Binding(
            self._type, provider, lifetime=lifetime or Transient(), enter=enter
        )
        self._registry.register(binding)


def _is_factory_a_provider(func: Factory[_T]) -> TypeGuard[Provider[_T]]:
    return bool(get_non_variadic_params(func))


def get_dependencies(
    function: Callable[..., Any], overrides: dict[str, type[Any]] | None = None
) -> dict[str, Dependency]:
    # Merge given callable inspected params with provided ones.
    # NOTE: we omit variadic params because we don't know how to autowire them yet
    params = get_non_variadic_params(function)
    for pname, override_type in (overrides or {}).items():
        params[pname] = params.get(
            pname, Parameter(pname, kind=Parameter.POSITIONAL_OR_KEYWORD)
        ).replace(annotation=override_type)

    if empty_params := get_untyped_parameters(params):
        # NOTE: if some parameters are missing type annotation we cannot autowire
        msg = f"Factory {function} is missing types for following parameters: {', '.join(empty_params)}"
        raise TypeError(msg)

    return {pname: Dependency.from_parameter(param) for pname, param in params.items()}


@dataclass(slots=True)
class Dependency:
    annotation: type[Any]
    default: Any = ...
    positional: bool = False

    @classmethod
    def from_parameter(cls, param: Parameter) -> Dependency:
        return Dependency(
            annotation=param.annotation,
            default=param.default if param.default != Parameter.empty else ...,
            positional=param.kind == Parameter.POSITIONAL_ONLY,
        )
