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
    context. This is to prevent containers to keep transient lifetime types for its whole
    duration and ensures proper release of any resolved resources.

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
        self._contexts = weakref.WeakSet[ResolutionContext]()

    def register(self, type_: type[_T]) -> RegistrationBuilder[_T]:
        """Register given type and define its resolution at runtime.

        This function returns a builder providing function for choosing the provider to
        use for resolving given type as well as its lifetime.
        """
        return RegistrationBuilder(self._registry, type_)

    def lookup(self, key: type[_T]) -> Registration[_T]:
        """Return registration for given type if any.

        :raise RegistrationNotFoundError: If the given type is not registered
        """
        registration = self._registry.get_registration(key)
        if registration is None:
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

        This is a shortand for `container.register(SomeType).use_factory(decorated_function)`
        Where `SomeType` is the return type annotation of a function named `decorated_function`

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
        """Release all cached singletons and exits their context managers if entered."""
        # TODO: create a test that ensure scopes are properly closed on container close
        for ctx in self._contexts:
            ctx.release()
        return super().release()

    def open_context(self) -> ResolutionContext:
        """Create and open a new resolution context for resolving types.

        You better use this function with a context manager. Otherwise call its release
        method when you're done with it.

        Note that the container automatically releases all opened context on release as
        long as those context are still referenced (not garbage collected)
        """
        ctx = ResolutionContext(self)
        self._contexts.add(ctx)
        return ctx


class ResolutionContext(Releasable["ResolutionContext"]):
    """Allow to resolve types from a container.

    It caches contextual types and enters context managers for both contextual and
    transient types. Cache is cleared on call to release method and all entered context
    managers are exited.
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
