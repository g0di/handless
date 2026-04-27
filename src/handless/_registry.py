from __future__ import annotations

import logging
from collections import defaultdict
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass, field
from inspect import Parameter, isasyncgenfunction, isclass, isgeneratorfunction
from types import EllipsisType
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, overload

from handless._utils import are_functions_equal, get_non_variadic_params
from handless.exceptions import BindingAlreadyExistsError, BindingError
from handless.lifetimes import Lifetime, Singleton, Transient

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

    from handless._container import Scope


class Registry:
    """Store and look up type bindings."""

    def __init__(self, *, allow_override: bool = False) -> None:
        self._logger = logging.getLogger(__name__)
        self._bindings: dict[type[Any], Binding[Any]] = {}
        self.allow_override = allow_override

    def register(self, binding: Binding[Any]) -> None:
        """Store a binding for later resolution.

        :param binding: Binding to store.
        :raises BindingAlreadyExistsError: If a binding already exists for the
            same type and overriding is disabled.
        """
        if not self.allow_override and binding.type_ in self._bindings:
            raise BindingAlreadyExistsError(binding.type_)

        self._bindings[binding.type_] = binding
        self._logger.info("Bound %s: %s", binding.type_, binding)

    def get_binding(self, type_: type[_T]) -> Binding[_T] | None:
        """Return binding for given type, or ``None`` if not bound.

        :param type_: Type to lookup.
        :returns: Matching binding or ``None``.
        """
        return self._bindings.get(type_)

    def clear(self) -> None:
        """Remove all bindings from this registry."""
        self._bindings.clear()


_T = TypeVar("_T")


@dataclass(slots=True, eq=False)
class Binding(Generic[_T]):
    """Describe how a specific type should be resolved.

    A binding maps a target type to a factory callable, lifetime policy,
    dependency list, and context management behavior.
    """

    type_: type[_T]
    """Bound type"""
    factory: Callable[
        ...,
        _T
        | Awaitable[_T]
        | AbstractContextManager[_T]
        | AbstractAsyncContextManager[_T],
    ]
    """Factory returning instances of the bound type"""
    managed: bool
    """Whether context managers returned by factory should be managed."""
    lifetime: Lifetime
    """Lifetime of the factory returned objects"""
    dependencies: tuple[Dependency, ...] = field(default_factory=tuple)
    """Dependencies to inject into the specified factory"""

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Binding)
            and self.type_ == value.type_
            and are_functions_equal(self.factory, value.factory)
            and self.managed == value.managed
            and self.lifetime == value.lifetime
            and self.dependencies == value.dependencies
        )


@dataclass(slots=True)
class Dependency:
    """Represent a single injectable dependency for a factory parameter.

    Dependencies are extracted from callable parameters and used to resolve
    arguments from a scope at runtime.
    """

    name: str
    type_: type[Any]
    default: Any = ...
    positional_only: bool = False

    @classmethod
    def from_parameter(
        cls, param: Parameter, type_: type[Any] | EllipsisType = ...
    ) -> Dependency:
        """Create a Dependency from a inspect.Parameter object.

        :param param: Inspected parameter to convert.
        :param type_: Optional type override for the parameter annotation.
        :returns: A dependency object inferred from the parameter.
        :raises TypeError: If no valid type annotation can be determined.
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


class Binder(Generic[_T]):
    """Builder for defining how a bound type should be resolved.

    Provides fluent API methods to specify the factory, lifetime, and management
    strategy for a bound type. Use one of ``to_self()``, ``to_value()``,
    ``to_factory()``, or ``to()`` to complete the binding.

    Example::

        >>> from handless import Container, Scoped
        >>> container = Container()
        >>> container.bind(str).to_value("config")
        >>> container.bind(list).to_self(lifetime=Scoped())
    """

    def __init__(self, registry: Registry, type_: type[_T]) -> None:
        self._registry = registry
        self._type = type_

    def to_self(
        self, lifetime: Lifetime | type[Lifetime] | None = None, *, managed: bool = True
    ) -> None:
        """Bind the type's constructor as its factory (standard constructor injection).

        This is the most common binding method. It automatically calls the type's
        ``__init__``, resolving any type-annotated parameters from the container.

        :param lifetime: Caching strategy as an instance or class, defaults to ``Transient``
            when omitted. Can pass a class like ``Singleton`` or an instance like
            ``Singleton()``.
        :param managed: Whether returned context managers are automatically managed.
        :raises BindingError: If constructor parameters lack type annotations.

        Example::

            >>> from handless import Container, Scoped, Singleton
            >>> class UserRepository:
            ...     def __init__(self, db: str):
            ...         self.db = db
            >>> container = Container()
            >>> container.bind(str).to_value("postgresql://localhost")
            >>> # Instance form:
            >>> container.bind(UserRepository).to_self(Scoped())
            >>> with container.create_scope() as scope:
            ...     repo = scope.resolve(UserRepository)
            ...     assert repo.db == "postgresql://localhost"
            >>> # Or pass the class without instantiation:
            >>> container2 = Container()
            >>> container2.bind(str).to_value("postgresql://localhost")
            >>> container2.bind(UserRepository).to_self(Scoped)
            >>> with container2.create_scope() as scope:
            ...     repo = scope.resolve(UserRepository)
            ...     assert repo.db == "postgresql://localhost"
        """
        self.to_factory(self._type, lifetime=lifetime, managed=managed)

    def to(self, alias_type: type[_T]) -> None:
        """Resolve the given type when resolving the bound one.

        :param alias_type: Target type that should be resolved for this binding.
        """
        self.to_factory(lambda c: c.resolve(alias_type), managed=False)

    @overload
    def to_value(self, value: _T, *, managed: bool = ...) -> None: ...

    # NOTE: following overload ensure managed is True when passing a context manager not being
    # an instance of _T
    @overload
    def to_value(
        self, value: AbstractContextManager[_T], *, managed: Literal[True]
    ) -> None: ...

    def to_value(self, value: Any, *, managed: bool = False) -> None:
        """Use given value when resolving the bound type.

        :param value: Concrete value to always return for this type.
        :param managed: Whether to manage context managers when ``value`` is one.
        """
        self.to_factory(lambda: value, lifetime=Singleton, managed=managed)

    @overload
    def to_factory(
        self,
        factory: Callable[[Scope], _T | Awaitable[_T]],
        lifetime: Lifetime | type[Lifetime] | None = ...,
        *,
        managed: bool = ...,
    ) -> None: ...

    @overload
    def to_factory(
        self,
        factory: Callable[
            [Scope],
            Iterator[_T]
            | AsyncIterator[_T]
            | AbstractContextManager[_T]
            | AbstractAsyncContextManager[_T],
        ],
        lifetime: Lifetime | type[Lifetime] | None = ...,
        *,
        managed: Literal[True] = ...,
    ) -> None: ...

    @overload
    def to_factory(
        self,
        factory: Callable[..., _T | Awaitable[_T]],
        lifetime: Lifetime | type[Lifetime] | None = ...,
        *,
        managed: bool = ...,
    ) -> None: ...

    @overload
    def to_factory(
        self,
        factory: Callable[
            ...,
            Iterator[_T]
            | AsyncIterator[_T]
            | AbstractContextManager[_T]
            | AbstractAsyncContextManager[_T],
        ],
        lifetime: Lifetime | type[Lifetime] | None = ...,
        *,
        managed: Literal[True] = ...,
    ) -> None: ...

    def to_factory(
        self,
        factory: Callable[..., Any],
        lifetime: Lifetime | type[Lifetime] | None = None,
        *,
        managed: bool = True,
    ) -> None:
        """Use a function or type to produce an instance of bound type when resolved.

        If the factory has parameters, it will be automatically resolved and injected on
        call. Parameters MUST have type annotation in order to be properly ressolved or a
        TypeError will be raised. An exception is made for single parameter function
        which will receive a `Scope` automatically if no type annotation is
        given.

        Note that variadic arguments (*args, **kwargs) are ignored.

        :param factory: Callable or type used to create resolved instances.
        :param lifetime: Resolution lifetime as an instance or class, defaults to
            ``Transient`` when omitted. Can pass a class like ``Singleton`` or an
            instance like ``Singleton()``.
        :param managed: Whether returned context managers are automatically managed.
        :raises BindingError: If dependency extraction fails.
        """
        if isasyncgenfunction(factory):
            factory = asynccontextmanager(factory)
        if isgeneratorfunction(factory):
            factory = contextmanager(factory)

        normalized_lifetime = (
            lifetime() if isinstance(lifetime, type) else (lifetime or Transient())
        )

        try:
            self._registry.register(
                Binding(
                    self._type,
                    factory,
                    lifetime=normalized_lifetime,
                    managed=managed,
                    dependencies=_collect_dependencies(factory),
                )
            )
        except TypeError as error:
            msg = f"Cannot bind {self._type} using {factory}: {error}"
            raise BindingError(msg) from error


def _collect_dependencies(
    function: Callable[..., Any], overrides: dict[str, type[Any]] | None = None
) -> tuple[Dependency, ...]:
    # Merge given callable inspected params with provided ones.
    # NOTE: we omit variadic params because we don't know how to autowire them yet
    from handless._container import Scope

    params = get_non_variadic_params(function)
    overrides = overrides or {}
    # Use a defaultdict that returns a Scope type if there is no override
    # for the given parameter name and the function has actually only one parameter.
    # This is to handle lambda expressions taking a single untyped parameter which is
    # expected to be a Scope.
    overrides_ = defaultdict[str, type[Any] | EllipsisType](
        lambda: Scope
        if len(params) == 1
        and next(iter(params.values())).annotation is Parameter.empty
        else ...,
        **overrides,
    )

    return tuple(
        Dependency.from_parameter(param, overrides_[name])
        for name, param in params.items()
    )
