from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless._lifetimes import Lifetime, LifetimeLiteral
from handless._lifetimes import parse as parse_lifetime
from handless._utils import get_first_param_name
from handless.containers import Container
from handless.providers import Provider

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless.registry import Registry

_T = TypeVar("_T")


@dataclass(slots=True, frozen=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: Provider[_T]
    enter: bool
    lifetime: LifetimeLiteral

    @cached_property
    def _lifetime(self) -> Lifetime:
        return parse_lifetime(self.lifetime)

    def resolve(self, container: Container) -> _T:
        return self._lifetime.accept(container, self)


class Binder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def to_self(
        self, lifetime: LifetimeLiteral = "transient", *, enter: bool = True
    ) -> Binding[_T]:
        return self.to_factory(self._type, lifetime=lifetime, enter=enter)

    def to(self, alias_type: type[_T]) -> Binding[_T]:
        return self.to_lambda(
            lambda c: c.get(alias_type), lifetime="transient", enter=False
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
        return self.to_factory(lambda: value, lifetime="singleton", enter=enter)

    def to_lambda(
        self,
        factory: Callable[[Container], _T],
        *,
        enter: bool = True,
        lifetime: LifetimeLiteral = "transient",
    ) -> Binding[_T]:
        return self.to_factory(
            factory,
            enter=enter,
            lifetime=lifetime,
            params={get_first_param_name(factory): Container},
        )

    @overload
    def to_factory(
        self,
        factory: Callable[..., _T],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: bool = ...,
        params: dict[str, type[Any]] | None = ...,
    ) -> Binding[_T]: ...

    # NOTE:: Following overload ensure enter is not False when passing a callable returning
    # context manager or an iterator not being an instance of _T
    @overload
    def to_factory(
        self,
        factory: Callable[..., Iterator[_T] | AbstractContextManager[_T]],
        *,
        lifetime: LifetimeLiteral = ...,
        enter: Literal[True] = ...,
        params: dict[str, type[Any]] | None = ...,
    ) -> Binding[_T]: ...

    # Overloads ensures that passing an iterator or a context manager which is NOT
    # an instance of _T requires enter=True

    def to_factory(
        self,
        factory: Callable[..., Any],
        *,
        lifetime: LifetimeLiteral = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Binding[_T]:
        binding = Binding(
            self._type, Provider(factory, params), lifetime=lifetime, enter=enter
        )
        self._registry.register(binding)
        return binding
