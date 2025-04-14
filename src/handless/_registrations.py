from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless import providers
from handless._lifetimes import Lifetime, LifetimeLiteral, Transient
from handless._lifetimes import parse as parse_lifetime

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless.containers import Container
    from handless.registry import Registry

_T = TypeVar("_T")


@dataclass(slots=True, frozen=True)
class Registration(Generic[_T]):
    type_: type[_T]
    provider: providers.Provider[_T]
    lifetime: Lifetime = field(default_factory=Transient)
    enter: bool = True

    def resolve(self, container: Container) -> _T:
        return self.lifetime.accept(container, self)


class RegistrationBuilder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def self(
        self, lifetime: LifetimeLiteral = "transient", *, enter: bool = True
    ) -> Registration[_T]:
        return self.factory(self._type, lifetime=lifetime, enter=enter)

    def alias(self, alias_type: type[_T]) -> Registration[_T]:
        provider = providers.Alias(alias_type)
        return self.provider(provider, "transient", enter=False)

    @overload
    def value(self, value: _T, *, enter: bool = ...) -> Registration[_T]: ...

    # NOTE: following overload ensure enter is True when passing a context manager not being
    # an instance of _T
    @overload
    def value(
        self, value: AbstractContextManager[_T], *, enter: Literal[True]
    ) -> Registration[_T]: ...

    def value(self, value: Any, *, enter: bool = False) -> Registration[_T]:
        provider = providers.Value(value)
        return self.provider(provider, "singleton", enter=enter)

    @overload
    def factory(
        self,
        factory: Callable[..., _T] = ...,
        lifetime: LifetimeLiteral = ...,
        *,
        enter: bool = ...,
    ) -> Registration[_T]: ...

    # NOTE:: Following overload ensure enter is not False when passing a callable returning
    # context manager or an iterator not being an instance of _T
    @overload
    def factory(
        self,
        factory: Callable[..., Iterator[_T] | AbstractContextManager[_T]],
        lifetime: LifetimeLiteral = ...,
        *,
        enter: Literal[True] = ...,
    ) -> Registration[_T]: ...

    # Overloads ensures that passing an iterator or a context manager which is NOT
    # an instance of _T requires enter=True

    def factory(
        self,
        factory: Callable[..., Any] | None = None,
        lifetime: LifetimeLiteral = "transient",
        *,
        enter: bool = True,
    ) -> Registration[_T]:
        provider = providers.Factory(factory or self._type)
        return self.provider(provider, lifetime, enter=enter)

    def dynamic(
        self,
        factory: Callable[[Container], _T],
        *,
        enter: bool = True,
        lifetime: LifetimeLiteral = "transient",
    ) -> Registration[_T]:
        provider = providers.Dynamic(factory)
        return self.provider(provider, enter=enter, lifetime=lifetime)

    def provider(
        self,
        provider: providers.Provider[_T],
        lifetime: LifetimeLiteral = "transient",
        *,
        enter: bool = True,
    ) -> Registration[_T]:
        registration = Registration(
            self._type, provider, lifetime=parse_lifetime(lifetime), enter=enter
        )
        self._registry[registration.type_] = registration
        return registration
