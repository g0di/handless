from __future__ import annotations

import logging
import weakref
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
)
from inspect import isasyncgenfunction, isgeneratorfunction
from typing import TYPE_CHECKING, Any, TypeVar, get_args, overload

from handless._registry import Binder, Registry
from handless._utils import get_return_type, isasynccontextmanager, iscontextmanager
from handless.exceptions import BindingError, BindingNotFoundError, ResolutionError
from handless.lifetimes import Releasable

if TYPE_CHECKING:
    from handless._registry import Binding
    from handless.lifetimes import Lifetime


_T = TypeVar("_T")
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_U = TypeVar("_U", bound=Callable[..., Any])


class Container(Releasable["Container"]):
    """Create a new container.

    Containers hold bindings defining how to resolve bound types. It also cache
    all singleton lifetime types. To resolve a type from a container you must open a scope.

    You're free to use the container in a context manager or to manually call the close
    method, both does the same. The close function does not prevent reusing the container;
    it only clears cached singletons and exits their context managers if entered.

    You should close your container when your application stops.
    You should create a scope anytime you need to resolve types and close it as soon as possible.
    For example, in a HTTP API, you may open one scope per request. For a message listener
    you may open one per message handling. For a CLI you open a scope per command received.

    >>> container = Container()
    >>> container.bind(str).to_value("Hello Container!")
    >>> with container.create_scope() as scope:
    ...     value = scope.resolve(str)
    ...     print(value)
    Hello Container!
    >>> container.close()
    """

    def __init__(self) -> None:
        super().__init__()
        self._registry = Registry()
        self._overrides = Registry(allow_override=True)
        self._scopes = weakref.WeakSet[Scope]()

    def bind(self, type_: type[_T]) -> Binder[_T]:
        """Bind given type and define its resolution at runtime.

        This function returns a builder providing function for choosing the provider to
        use for resolving given type as well as its lifetime.

        >>> container = Container()
        >>> container.bind(str).to_value("handless")
        >>> container.bind(object).to_factory(lambda: object())
        >>> container.bind(Any).to(object)
        >>> container.bind(list).to_self()

        :param type_: Type to bind.
        :returns: A binding builder for configuring value, factory, alias, or self.
        """
        return Binder(self._registry, type_)

    def override(self, type_: type[_T]) -> Binder[_T]:
        """Temporarily override a type binding (for testing).

        Overrides take precedence over normal bindings and are useful for
        injecting test doubles (mocks, stubs, fakes) into your code without
        modifying the container's base bindings.

        The override registry is cleared when you call :meth:`close`, allowing
        the same container instance to be reused for multiple test runs.

        :param type_: Type to override.
        :returns: A binding builder for defining the override provider.

        Example::

            >>> from unittest.mock import Mock
            >>> container = Container()
            >>> container.bind(str).to_value("production-db-url")
            >>>
            >>> # Use production config in normal scope
            >>> with container.create_scope() as scope:
            ...     config = scope.resolve(str)
            ...     assert "production" in config
            >>>
            >>> # Override for testing
            >>> container.override(str).to_value("test-db-url")
            >>> with container.create_scope() as scope:
            ...     config = scope.resolve(str)
            ...     assert "test" in config
            >>>
            >>> # Clean up - removes all overrides
            >>> container.close()
            >>> with container.create_scope() as scope:
            ...     config = scope.resolve(str)
            ...     assert "production" in config
        """
        return Binder(self._overrides, type_)

    def lookup(self, key: type[_T]) -> Binding[_T]:
        """Return binding for given type if any.

        >>> container = Container()
        >>> container.bind(str).to_value("handless")
        >>> container.lookup(str)
        Binding(type_=<class 'str'>, ...)

        If the given type is not bound
        >>> container = Container()
        >>> container.lookup(str)
        Traceback (most recent call last):
            ...
        handless.exceptions.BindingNotFoundError: ...

        :param key: Bound type key to retrieve.
        :returns: Binding bound to ``key``.
        :raises BindingNotFoundError: If the given type is not bound.
        """
        binding = self._overrides.get_binding(key) or self._registry.get_binding(key)
        if not binding:
            raise BindingNotFoundError(key)
        return binding

    @overload
    def binding(self, factory: _U) -> _U: ...

    @overload
    def binding(
        self, *, managed: bool = ..., lifetime: Lifetime | type[Lifetime] | None = ...
    ) -> Callable[[_U], _U]: ...

    def binding(
        self,
        factory: _U | None = None,
        *,
        managed: bool = True,
        lifetime: Lifetime | type[Lifetime] | None = None,
    ) -> Any:
        """Declare a function as a factory binding for its return type annotation.

        This decorator extracts the return type from the decorated function and
        registers it as a factory binding. It is equivalent to calling
        `container.bind(SomeType).to_factory(decorated_function)` where `SomeType`
        is inferred from the function's return type annotation.

        The decorated function is left untouched, so you can safely call it directly
        in your code in addition to having it registered with the container.

        Example::

            >>> container = Container()
            >>> @container.binding
            ... def get_database() -> Database:
            ...     return Database()
            >>> # Now Database is bound, and you can also call the function directly
            >>> db = get_database()
            >>> # Or resolve it from a scope
            >>> with container.create_scope() as scope:
            ...     db = scope.resolve(Database)

        :param factory: The decorated factory function (function parameter only used internally)
        :param managed: Whether returned context managers should be entered/exited automatically.
        :param lifetime: The binding lifetime, defaults to `Transient`
        :returns: The unmodified decorated function.
        :raises BindingError: If the decorated function has no return type annotation.
        """

        def wrapper(factory: _U) -> _U:
            rettype = get_return_type(factory)
            if (
                isgeneratorfunction(factory)
                or isasyncgenfunction(factory)
                or iscontextmanager(factory)
                or isasynccontextmanager(factory)
            ):
                rettype = get_args(rettype)[0]
            if not rettype:
                msg = f"{factory} has no return type annotation"
                raise BindingError(msg)

            self.bind(rettype).to_factory(factory, lifetime=lifetime, managed=managed)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def close(self) -> None:
        """Close all cached singletons and opened scopes.

        This also exits any entered context managers for singleton lifetime objects.
        Note that opened scopes are weakly referenced meaning that only ones still
        referenced will be closed.

        This method is idempotent and can safely be called multiple times.
        Calling it never prevents resolving new values with the same container afterwards.
        """
        for scope in self._scopes:
            scope.close()
        self._overrides.clear()
        return super().close()

    def create_scope(self) -> Scope:
        """Create and open a new scope for resolving types.

        You better use this function with a context manager. Otherwise call its close
        method when you're done with it.

        :returns: A new scope bound to this container.
        """
        scope = Scope(self)
        self._scopes.add(scope)
        return scope

    @overload
    def resolve(self, type_: type[_T1], /) -> AbstractContextManager[_T1]: ...

    @overload
    def resolve(
        self, type_: type[_T1], type2: type[_T2], /
    ) -> AbstractContextManager[tuple[_T1, _T2]]: ...

    @overload
    def resolve(
        self, type_: type[_T1], type2: type[_T2], type3: type[_T3], /
    ) -> AbstractContextManager[tuple[_T1, _T2, _T3]]: ...

    @overload
    def resolve(
        self, type_: type[_T1], type2: type[_T2], type3: type[_T3], type4: type[_T4], /
    ) -> AbstractContextManager[tuple[_T1, _T2, _T3, _T4]]: ...

    @contextmanager
    def resolve(self, type_: type[Any], /, *types: type[Any]) -> Iterator[Any]:
        """Resolve one or several types using a temporary scope.

        This is a shorthand for opening a scope, resolving type(s), yielding
        result(s), then closing that scope on context exit.

        When resolving a single type, the yielded value is the resolved object.
        When resolving several types, the yielded value is a tuple preserving the
        order of requested types.

        >>> container = Container()
        >>> container.bind(str).to_value("handless")
        >>> with container.resolve(str) as value:
        ...     print(value)
        handless

        :param type_: First type to resolve.
        :param types: Optional additional types to resolve in order.
        :yields: One resolved object for a single type, otherwise a tuple of resolved objects.
        """
        requested_types = (type_, *types)
        with self.create_scope() as scope:
            values = tuple(
                scope.resolve(requested_type) for requested_type in requested_types
            )
            if not types:
                yield values[0]
                return
            yield values

    @overload
    def aresolve(self, type_: type[_T1], /) -> AbstractAsyncContextManager[_T1]: ...

    @overload
    def aresolve(
        self, type_: type[_T1], type2: type[_T2], /
    ) -> AbstractAsyncContextManager[tuple[_T1, _T2]]: ...

    @overload
    def aresolve(
        self, type_: type[_T1], type2: type[_T2], type3: type[_T3], /
    ) -> AbstractAsyncContextManager[tuple[_T1, _T2, _T3]]: ...

    @overload
    def aresolve(
        self, type_: type[_T1], type2: type[_T2], type3: type[_T3], type4: type[_T4], /
    ) -> AbstractAsyncContextManager[tuple[_T1, _T2, _T3, _T4]]: ...

    @asynccontextmanager
    async def aresolve(
        self, type_: type[Any], /, *types: type[Any]
    ) -> AsyncIterator[Any]:
        """Asynchronously resolve one or several types using a temporary scope.

        This is the async counterpart of :meth:`resolve`.

        :param type_: First type to resolve.
        :param types: Optional additional types to resolve in order.
        :yields: One resolved object for a single type, otherwise a tuple of resolved objects.
        """
        requested_types = (type_, *types)
        async with self.create_scope() as scope:
            values = [
                await scope.aresolve(requested_type)
                for requested_type in requested_types
            ]
            if not types:
                yield values[0]
                return
            yield tuple(values)


class Scope(Releasable["Scope"]):
    """Allow to resolve types from a container.

    It caches scoped types and enters context managers for both scoped and
    transient types. Cache is cleared on call to close method and all entered context
    managers are exited.

    >>> container = Container()
    >>> container.bind(str).to_value("handless")
    >>> with container.create_scope() as scope:
    ...     scope.resolve(str)
    'handless'
    """

    def __init__(self, container: Container) -> None:
        """Create a new scope for the given container.

        Note that this constructor is not intended to be used directly.
        Prefer using `container.create_scope()` instead.

        :param container: Parent container associated with this scope.
        """
        super().__init__()
        self._container = container
        self._registry = Registry()
        self._logger = logging.getLogger(__name__)

    @property
    def container(self) -> Container:
        """Return the parent container of this scope."""
        return self._container

    def bind_local(self, type_: type[_T]) -> Binder[_T]:
        """Bind a type only within this scope (doesn't affect the container).

        Local bindings are scope-specific and don't modify the parent container.
        They take precedence over container bindings when resolving within this scope.

        Useful for:
        - Per-request customization in HTTP handlers
        - Temporary test fixtures within a single test
        - Scope-local state that shouldn't affect other scopes

        :param type_: Type to bind only in this scope.
        :returns: A binding builder for defining the local provider.

        Example::

            >>> container = Container()
            >>> container.bind(str).to_value("global")
            >>>
            >>> with container.create_scope() as scope:
            ...     # Override just for this scope
            ...     scope.bind_local(str).to_value("scope-local")
            ...     assert scope.resolve(str) == "scope-local"
            >>>
            >>> # Other scopes unaffected
            >>> with container.create_scope() as scope2:
            ...     assert scope2.resolve(str) == "global"
        """
        return Binder(self._registry, type_)

    def resolve(self, type_: type[_T]) -> _T:
        """Resolve a type to get an instance.

        Looks up the provider from this scope's local registry first, then from the
        parent container if not found. Automatically injects any bound dependencies
        required by the factory.

        The behavior depends on the bound lifetime:
        - **Transient**: Creates a new instance every time
        - **Scoped**: Caches within this scope, new instance per scope
        - **Singleton**: Caches in the container, same instance everywhere

        :param type_: The type to resolve (must be bound).
        :returns: An instance of the bound type, with dependencies injected.
        :raises BindingNotFoundError: If the type was never bound.
        :raises ResolutionError: If resolution fails (e.g. missing dependencies).

        Example::

            >>> container = Container()
            >>> container.bind(str).to_value("hello")
            >>> with container.create_scope() as scope:
            ...     msg = scope.resolve(str)
            ...     print(msg)
            hello

        See Also:
            aresolve: Async version for async factories
            bind_local: For scope-specific bindings
        """
        if type_ is type(self):
            return self

        binding = self._lookup(type_)

        try:
            value = binding.lifetime.resolve(self, binding)
            self._logger.info("Resolved %s: %s -> %s", type_, binding, type(value))
        except Exception as error:
            raise ResolutionError(type_) from error
        else:
            return value

    async def aresolve(self, type_: type[_T]) -> _T:
        """Asynchronously resolve a type to get an instance.

        This is the async variant of :meth:`resolve`. Use this when:
        - The factory is an async function (async def)
        - The factory is an async generator (async context manager)
        - Any dependencies are async-resolvable

        All other behavior is identical to :meth:`resolve`:
        - Looks up from local scope first, then container
        - Injects dependencies automatically
        - Respects bound lifetimes
        - Can create new instances or return cached ones

        :param type_: The type to resolve (must be bound).
        :returns: An instance of the bound type, with dependencies injected.
        :raises BindingNotFoundError: If the type was never bound.
        :raises ResolutionError: If resolution fails.

        Example::

            >>> import asyncio
            >>> from handless import Container
            >>>
            >>> async def get_config() -> dict:
            ...     return {"debug": True}
            >>>
            >>> container = Container()
            >>> container.bind(dict).to_factory(get_config)
            >>>
            >>> async def main():
            ...     async with container.create_scope() as scope:
            ...         config = await scope.aresolve(dict)
            ...         print(config)
            >>>
            >>> asyncio.run(main())
            {'debug': True}

        See Also:
            resolve: Sync version for sync factories
            Lifetime: Explains caching behavior
        """
        if type_ is type(self):
            return self

        binding = self._lookup(type_)

        try:
            value = await binding.lifetime.aresolve(self, binding)
            self._logger.info("Resolved %s: %s -> %s", type_, binding, type(value))
        except Exception as error:
            raise ResolutionError(type_) from error
        else:
            return value

    def _lookup(self, type_: type[_T]) -> Binding[_T]:
        return self._registry.get_binding(type_) or self._container.lookup(type_)
