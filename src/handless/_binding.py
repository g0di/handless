from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless import _provider
from handless._lifetime import Lifetime, LifetimeLiteral, Transient
from handless._lifetime import parse as parse_lifetime

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless._container import Container

_T = TypeVar("_T")


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: _provider.Provider[_T]
    lifetime: Lifetime = field(default_factory=Transient)
    enter: bool = True

    def resolve(self, container: Container) -> _T:
        return self.lifetime.accept(container, self)


class Binder(Generic[_T]):
    def __init__(self, type_: type[_T]) -> None:
        self.type_ = type_

    def to(self, alias_type: type[_T]) -> Binding[_T]:
        """Bind type to given alias.

        When resolved, the given type will be resolved and returned instead
        """
        provider = _provider.Alias(alias_type)
        return self.to_provider(provider, lifetime="transient", enter=False)

    def to_self(self, lifetime: LifetimeLiteral = "transient") -> Binding[_T]:
        """Bind type to itself.

        When resolved, the type will be used to get an instance of the type.
        :param lifetime: _description_, defaults to "transient"
        :return: _description_
        """
        provider = _provider.Factory(self.type_)
        return self.to_provider(provider, lifetime=lifetime)

    @overload
    def to_value(self, value: _T, *, enter: bool = ...) -> Binding[_T]: ...

    @overload
    def to_value(
        self, value: AbstractContextManager[_T], *, enter: Literal[True]
    ) -> Binding[_T]: ...

    def to_value(self, value: Any, *, enter: bool = False) -> Binding[_T]:
        provider = _provider.Value(value)
        return self.to_provider(provider, lifetime="singleton", enter=enter)

    @overload
    def to_factory(
        self,
        factory: Callable[..., Iterator[_T] | AbstractContextManager[_T]],
        lifetime: LifetimeLiteral = ...,
        *,
        enter: Literal[True] = ...,
    ) -> Binding[_T]: ...

    @overload
    def to_factory(
        self,
        factory: Callable[..., _T],
        lifetime: LifetimeLiteral = ...,
        *,
        enter: bool = ...,
    ) -> Binding[_T]: ...

    # Overloads ensures that passing an iterator or a context manager which is NOT
    # an instance of _T requires enter=True

    def to_factory(
        self,
        factory: Callable[..., Any],
        lifetime: LifetimeLiteral = "transient",
        *,
        enter: bool = True,
    ) -> Binding[_T]:
        provider = _provider.Factory(factory)
        return self.to_provider(provider, lifetime=lifetime, enter=enter)

    def to_lambda(
        self,
        factory: Callable[[Container], _T],
        lifetime: LifetimeLiteral = "transient",
        *,
        enter: bool = True,
    ) -> Binding[_T]:
        provider = _provider.Lambda(factory)
        return self.to_provider(provider, lifetime=lifetime, enter=enter)

    def to_provider(
        self,
        provider: _provider.Provider[_T],
        lifetime: LifetimeLiteral = "transient",
        *,
        enter: bool = True,
    ) -> Binding[_T]:
        return Binding(
            self.type_, provider, lifetime=parse_lifetime(lifetime), enter=enter
        )
