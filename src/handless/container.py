from __future__ import annotations

import logging
import weakref
from collections.abc import Callable
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, TypeVar, get_args, overload

from handless._registry import RegistrationBuilder, Registry
from handless._utils import get_return_type, iscontextmanager
from handless.exceptions import (
    RegistrationError,
    RegistrationNotFoundError,
    ResolutionError,
)
from handless.lifetimes import Releasable

if TYPE_CHECKING:
    from handless._registry import Registration
    from handless.lifetimes import Lifetime


_T = TypeVar("_T")
_U = TypeVar("_U", bound=Callable[..., Any])


class Container(Releasable["Container"]):
    """Create a new container.

    Containers hold registrations defining how to resolve registered types. It also cache
    all singleton lifetime types. To resolve a type from a container you must open a resolution
    context.

    You're free to use the container in a context manager or to manually call the release
    method, both does the same. The release function does not prevent to reuse the container
    it just clears all cached singleton and exits their context manager if entered.

    You should release your container when your application stops.
    You should open context anytime you need to resolve types and release it as soon as possible.
    For example, in a HTTP API, you may open one context per request. For a message listener
    you may open one per message handling. For a CLI you open a context per command received.

    >>> container = Container()
    >>> container.register(str).value("Hello Container!")
    >>> with container.open_context() as ctx:
    ...     value = ctx.resolve(str)
    ...     print(value)
    Hello Container!
    >>> container.release()
    """

    def __init__(self) -> None:
        super().__init__()
        self._registry = Registry()
        self._overrides = Registry(allow_override=True)
        self._contexts = weakref.WeakSet[ResolutionContext]()

    def register(self, type_: type[_T]) -> RegistrationBuilder[_T]:
        """Register given type and define its resolution at runtime.

        This function returns a builder providing function for choosing the provider to
        use for resolving given type as well as its lifetime.

        >>> container = Container()
        >>> container.register(str).value("handless")
        >>> container.register(object).factory(lambda: object())
        >>> container.register(Any).alias(object)
        >>> container.register(list).self()
        """
        return RegistrationBuilder(self._registry, type_)

    def override(self, type_: type[_T]) -> RegistrationBuilder[_T]:
        return RegistrationBuilder(self._overrides, type_)

    def lookup(self, key: type[_T]) -> Registration[_T]:
        """Return registration for given type if any.

        >>> container = Container()
        >>> container.register(str).value("handless")
        >>> container.lookup(str)
        Registration(type_=<class 'str'>, ...)

        If the given type is not registered
        >>> container = Container()
        >>> container.lookup(str)
        Traceback (most recent call last):
            ...
        handless.exceptions.RegistrationNotFoundError: ...

        :raise RegistrationNotFoundError: If the given type is not registered
        """
        registration = self._overrides.get_registration(
            key
        ) or self._registry.get_registration(key)
        if not registration:
            raise RegistrationNotFoundError(key)
        return registration

    @overload
    def factory(self, factory: _U) -> _U: ...

    @overload
    def factory(
        self, *, enter: bool = ..., lifetime: Lifetime = ...
    ) -> Callable[[_U], _U]: ...

    def factory(
        self,
        factory: _U | None = None,
        *,
        enter: bool = True,
        lifetime: Lifetime | None = None,
    ) -> Any:
        """Register decorated function as a factory for its return type annotation.

        This is a shortand for `container.register(SomeType).factory(decorated_function)`
        Where `SomeType` is the return type annotation of `decorated_function`.

        Decorated function is left untouched meaning that you can  safely call it manually.

        :param factory: The decorated factory function
        :param lifetime: The factory lifetime, defaults to `Transient`
        :return: The pristine decorated function
        """

        def wrapper(factory: _U) -> _U:
            rettype = get_return_type(factory)
            if isgeneratorfunction(factory) or iscontextmanager(factory):
                rettype = get_args(rettype)[0]
            if not rettype:
                msg = f"{factory} has no return type annotation"
                raise RegistrationError(msg)

            self.register(rettype).factory(factory, lifetime=lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def release(self) -> None:
        """Release all cached singletons and opened contexts.

        This will also exits any entered context managers for singleton lifetime objects.
        Note that opened contexts are weakly referenced meaning that only ones still
        referenced will be released.

        This method is safe to be called several times, it does not prevent from using
        the container.
        """
        # TODO: create a test that ensure scopes are properly closed on container close
        for ctx in self._contexts:
            ctx.release()
        self._overrides.clear()
        return super().release()

    def open_context(self) -> ResolutionContext:
        """Create and open a new resolution context for resolving types.

        You better use this function with a context manager. Otherwise call its release
        method when you're done with it.
        """
        ctx = ResolutionContext(self)
        self._contexts.add(ctx)
        return ctx


class ResolutionContext(Releasable["ResolutionContext"]):
    """Allow to resolve types from a container.

    It caches contextual types and enters context managers for both contextual and
    transient types. Cache is cleared on call to release method and all entered context
    managers are exited.

    >>> container = Container()
    >>> container.register(str).value("handless")
    >>> with container.open_context() as ctx:
    ...     ctx.resolve(str)
    'handless'
    """

    def __init__(self, container: Container) -> None:
        """Create a new resolution context for the given container.

        Note that this constructor is not intended to be used directly.
        Prefer using `container.open_context()` instead.
        """
        super().__init__()
        self._container = container
        self._registry = Registry()
        self._logger = logging.getLogger(__name__)

    @property
    def container(self) -> Container:
        """Return the parent container of this context."""
        return self._container

    def register_local(self, type_: type[_T]) -> RegistrationBuilder[_T]:
        return RegistrationBuilder(self._registry, type_)

    def resolve(self, type_: type[_T]) -> _T:
        """Resolve given type by returning an instance of it using the provider registered.

        The provider is looked up from this context local registry first then from its
        parent container if not found.
        """
        if type_ is type(self):
            return self

        registration = self._lookup(type_)

        try:
            value = registration.lifetime.resolve(self, registration)
            self._logger.info("Resolved %s: %s -> %s", type_, registration, type(value))
        except Exception as error:
            raise ResolutionError(type_) from error
        else:
            return value

    def _lookup(self, type_: type[_T]) -> Registration[_T]:
        return self._registry.get_registration(type_) or self._container.lookup(type_)
