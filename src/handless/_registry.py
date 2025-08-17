from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isclass, isgeneratorfunction
from types import EllipsisType
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless._utils import are_functions_equal, get_non_variadic_params
from handless.exceptions import RegistrationAlreadyExistError, RegistrationError
from handless.lifetimes import Lifetime, Singleton, Transient

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from handless.container import ResolutionContext


class Registry:
    """Register object types and define how to resolve them."""

    def __init__(self, *, allow_override: bool = False) -> None:
        self._logger = logging.getLogger(__name__)
        self._registrations: dict[type[Any], Registration[Any]] = {}
        self.allow_override = allow_override

    def register(self, registration: Registration[Any]) -> None:
        if not self.allow_override and registration.type_ in self._registrations:
            raise RegistrationAlreadyExistError(registration.type_)

        self._registrations[registration.type_] = registration
        self._logger.info("Registered %s: %s", registration.type_, registration)

    def get_registration(self, type_: type[_T]) -> Registration[_T] | None:
        return self._registrations.get(type_)

    def clear(self) -> None:
        self._registrations.clear()


_T = TypeVar("_T")


@dataclass(slots=True, eq=False)
class Registration(Generic[_T]):
    type_: type[_T]
    """Registered type"""
    factory: Callable[..., _T | AbstractContextManager[_T]]
    """Factory returning instances of the registered type"""
    enter: bool
    """Whether or not enters context managers returned by factory function"""
    lifetime: Lifetime
    """Lifetime of the factory returned objects"""
    dependencies: tuple[Dependency, ...] = field(default_factory=tuple)
    """Dependencies to inject into the specified factory"""

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Registration)
            and self.type_ == value.type_
            and are_functions_equal(self.factory, value.factory)
            and self.enter == value.enter
            and self.lifetime == value.lifetime
            and self.dependencies == value.dependencies
        )


@dataclass(slots=True)
class Dependency:
    name: str
    type_: type[Any]
    default: Any = ...
    positional_only: bool = False

    @classmethod
    def from_parameter(
        cls, param: Parameter, type_: type[Any] | EllipsisType = ...
    ) -> Dependency:
        """Create a Dependency from a inspect.Parameter object.

        :param type_: Can be provided to override the type annotation of the given parameter
        """
        actual_type = param.annotation if type_ is ... else type_
        if actual_type is Parameter.empty:
            msg = f"Parameter {param.name} is missing type annotation"
            raise TypeError(msg)
        if not isclass(actual_type):
            msg = f"Parameter {param.name} type annotation {param.annotation} is not a type"
            raise TypeError(msg)

        return cls(
            name=param.name,
            type_=actual_type,
            default=param.default if param.default != Parameter.empty else ...,
            positional_only=param.kind is Parameter.POSITIONAL_ONLY,
        )


class RegistrationBuilder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def self(self, *, lifetime: Lifetime | None = None, enter: bool = True) -> None:
        self.factory(self._type, lifetime=lifetime, enter=enter)

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
        self.factory(lambda: value, lifetime=Singleton(), enter=enter)

    @overload
    def factory(
        self,
        factory: Callable[[ResolutionContext], _T],
        *,
        lifetime: Lifetime | None = ...,
        enter: bool = ...,
    ) -> None: ...

    @overload
    def factory(
        self,
        factory: Callable[
            [ResolutionContext], Iterator[_T] | AbstractContextManager[_T]
        ],
        *,
        lifetime: Lifetime | None = ...,
        enter: Literal[True] = ...,
    ) -> None: ...

    @overload
    def factory(
        self,
        factory: Callable[..., _T],
        *,
        lifetime: Lifetime | None = ...,
        enter: bool = ...,
    ) -> None: ...

    @overload
    def factory(
        self,
        factory: Callable[..., Iterator[_T] | AbstractContextManager[_T]],
        *,
        lifetime: Lifetime | None = ...,
        enter: Literal[True] = ...,
    ) -> None: ...

    def factory(
        self,
        factory: Callable[..., Any],
        *,
        lifetime: Lifetime | None = None,
        enter: bool = True,
    ) -> None:
        """Use a function or type to produce an instance of registered type when resolved.

        If the factory has parameters, it will be automatically resolved and injected on
        call. Parameters MUST have type annotation in order to be properly ressolved or a
        TypeError will be raised. An exception is made for single parameter function
        which will receive a `ResolutionContext` automatically if no type annotation is
        given.

        Note that variadic arguments (*args, **kwargs) are ignored.
        """
        if isgeneratorfunction(factory):
            factory = contextmanager(factory)

        try:
            self._registry.register(
                Registration(
                    self._type,
                    factory,
                    lifetime=lifetime or Transient(),
                    enter=enter,
                    dependencies=_collect_dependencies(factory),
                )
            )
        except TypeError as error:
            msg = f"Cannot register {self._type} using {factory}: {error}"
            raise RegistrationError(msg) from None


def _collect_dependencies(
    function: Callable[..., Any], overrides: dict[str, type[Any]] | None = None
) -> tuple[Dependency, ...]:
    # Merge given callable inspected params with provided ones.
    # NOTE: we omit variadic params because we don't know how to autowire them yet
    from handless.container import ResolutionContext

    params = get_non_variadic_params(function)
    overrides = overrides or {}
    # Use a defaultdict that returns a ResolutionContext type if there is no override
    # for the given parameter name and the function has actually only one parameter.
    # This is to handle lambda expressions taking a single untyped parameter which is
    # expected to be a ResolutionContext.
    overrides_ = defaultdict[str, type[Any] | EllipsisType](
        lambda: ResolutionContext
        if len(params) == 1
        and next(iter(params.values())).annotation is Parameter.empty
        else ...,
        **overrides,
    )

    return tuple(
        Dependency.from_parameter(param, overrides_[name])
        for name, param in params.items()
    )
