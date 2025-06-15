from __future__ import annotations

import logging
import weakref
from collections.abc import Callable
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, TypeVar, get_args, overload

from handless._bindings import Binder
from handless._registry import Registry
from handless._utils import get_return_type, iscontextmanager
from handless.exceptions import BindingNotFoundError, ResolutionError
from handless.lifetimes import Releasable

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.lifetimes import Lifetime


_T = TypeVar("_T")
_U = TypeVar("_U", bound=Callable[["Scope"], Any])


class Container(Releasable["Container"]):
    def __init__(self) -> None:
        super().__init__()
        self._registry = Registry()
        self._scopes = weakref.WeakSet[Scope]()

    def lookup(self, key: type[_T]) -> Binding[_T]:
        """Return binding registered for given type or raise a BindingNotFoundError."""
        binding = self._registry.get_binding(key)
        if binding is None:
            raise BindingNotFoundError(key)
        return binding

    def register(self, type_: type[_T]) -> Binder[_T]:
        """Register given type and define its resolution at runtime."""
        return Binder(self._registry, type_)

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
        """Register decorated function as a provider for its return type annotation.

        :param factory: The decorated factory function, defaults to None
        :param lifetime: The factory lifetime, defaults to "transient"
        :return: The pristine function
        """

        def wrapper(factory: _U) -> _U:
            rettype = get_return_type(factory)
            if isgeneratorfunction(factory) or iscontextmanager(factory):
                rettype = get_args(rettype)[0]
            if not rettype:
                msg = f"{factory} has no return type annotation"
                raise TypeError(msg)

            self.register(rettype).factory(factory, lifetime=lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def release(self) -> None:
        # TODO: create a test that ensure scopes are properly closed on container close
        for scope in self._scopes:
            scope.release()
        return super().release()

    def create_scope(self) -> Scope:
        scope = Scope(self)
        self._scopes.add(scope)
        return scope


# TODO: introduce a protocol defining only the resolve method that will be passed to
# providers at resolution time to avoid users from consuming scope object methods at that time.

# TODO: pass the Scope class as a private one and only expose its protocol to prevent
# users from creating them by hand.


class Scope(Releasable["Scope"]):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self._container = container
        self._registry = Registry()
        self._logger = logging.getLogger(__name__)

        # NOTE: If user creates the scope manually, we get his back covered
        self._container._scopes.add(self)  # noqa: SLF001

    @property
    def container(self) -> Container:
        return self._container

    def register_local(self, type_: type[_T]) -> Binder[_T]:
        return Binder(self._registry, type_)

    def resolve(self, type_: type[_T]) -> _T:
        binding = self._lookup(type_)

        try:
            value = binding.lifetime.resolve(self, binding)
            self._logger.info("Resolved %s: %s -> %s", type_, binding, type(value))
        except Exception as error:
            raise ResolutionError(type_) from error
        else:
            return value

    def _lookup(self, type_: type[_T]) -> Binding[_T]:
        return self._registry.get_binding(type_) or self._container.lookup(type_)
