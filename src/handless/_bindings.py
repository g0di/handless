from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isgeneratorfunction
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless._lifetimes import Lifetime, LifetimeLiteral
from handless._lifetimes import parse as parse_lifetime
from handless._utils import (
    compare_functions,
    get_non_variadic_params,
    get_untyped_parameters,
)
from handless.containers import Container

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless.registry import Registry

_T = TypeVar("_T")


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: Callable[..., _T | AbstractContextManager[_T]]
    enter: bool
    lifetime: Lifetime
    dependencies: dict[str, Dependency] = field(default_factory=dict)

    def resolve(self, container: Container) -> _T:
        return self.lifetime.accept(container, self)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Binding)
            and self.type_ == value.type_
            and compare_functions(self.provider, value.provider)
            and self.enter == value.enter
            and self.lifetime == value.lifetime
            and self.dependencies == value.dependencies
        )


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


class Binder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def to_self(
        self, lifetime: LifetimeLiteral = "transient", *, enter: bool = True
    ) -> Binding[_T]:
        return self.to_provider(self._type, lifetime=lifetime, enter=enter)

    def to(self, alias_type: type[_T]) -> Binding[_T]:
        return self.to_provider(
            lambda alias: alias,
            lifetime="transient",
            enter=False,
            params={"alias": alias_type},
        )

    @overload
    def to_value(self, value: _T, *, enter: bool = ...) -> Binding[_T]: ...

    # NOTE: following overload ensure enter is True when passing a context manager not being
    # an instance of _T
    @overload
    def to_value(
        self, value: AbstractContextManager[_T], *, enter: Literal[True]
    ) -> Binding[_T]: ...

    def to_value(self, value: Any, *, enter: bool = False) -> Binding[_T]:
        return self.to_provider(lambda: value, lifetime="singleton", enter=enter)

    @overload
    def to_factory(
        self,
        factory: Callable[[Container], _T],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: bool = ...,
    ) -> Binding[_T]: ...

    # NOTE:: Following overload ensure enter is not False when passing a callable returning
    # context manager or an iterator not being an instance of _T
    @overload
    def to_factory(
        self,
        factory: Callable[[Container], AbstractContextManager[_T]],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: Literal[True] = ...,
    ) -> Binding[_T]: ...

    def to_factory(
        self,
        factory: Callable[..., Any],
        *,
        lifetime: LifetimeLiteral = "transient",
        enter: bool = True,
    ) -> Binding[_T]:
        return self.to_provider(
            # NOTE: using a lambda here avoid issues where the given function is
            # is wrapped and the actual parameter name does not match the wrapped one
            lambda container: factory(container),
            enter=enter,
            lifetime=lifetime,
            params={"container": Container},
        )

    @overload
    def to_provider(
        self,
        provider: Callable[..., _T],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: bool = ...,
        params: dict[str, type[Any]] | None = ...,
    ) -> Binding[_T]: ...

    # NOTE:: Following overload ensure enter is not False when passing a callable returning
    # context manager or an iterator not being an instance of _T
    @overload
    def to_provider(
        self,
        provider: Callable[..., Iterator[_T] | AbstractContextManager[_T]],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: Literal[True] = ...,
        params: dict[str, type[Any]] | None = ...,
    ) -> Binding[_T]: ...

    # Overloads ensures that passing an iterator or a context manager which is NOT
    # an instance of _T requires enter=True

    def to_provider(
        self,
        provider: Callable[..., Any],
        *,
        lifetime: LifetimeLiteral = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Binding[_T]:
        if isgeneratorfunction(provider):
            provider = contextmanager(provider)
        binding = Binding(
            self._type,
            provider,
            lifetime=parse_lifetime(lifetime),
            enter=enter,
            dependencies=get_dependencies(provider, overrides=params),
        )
        self._registry.register(binding)
        return binding


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
