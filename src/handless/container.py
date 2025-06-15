from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, TypeVar, get_args, overload

from handless._bindings import Binder
from handless._registry import Registry
from handless._utils import get_return_type, iscontextmanager
from handless.exceptions import BindingNotFoundError, ResolutionError

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.lifetimes import Lifetime


_T = TypeVar("_T")
_U = TypeVar("_U", bound=Callable[["Scope"], Any])
CloseCallback = Callable[[], Any]


class Releasable(AbstractContextManager[_T]):
    """Supports release method and registering callbacks on release."""

    def __init__(self) -> None:
        self._on_release_callbacks: list[CloseCallback] = []

    def __exit__(self, *args: object) -> None:
        self.release()

    def on_release(self, callback: CloseCallback) -> None:
        self._on_release_callbacks.append(callback)

    def release(self) -> None:
        """Release cached instances and exit entered context managers.

        Note that the object is still fully usable afterwards.
        """
        for cb in self._on_release_callbacks:
            cb()


class Container(Releasable["Container"]):
    def __init__(self) -> None:
        super().__init__()
        self._registry = Registry()

    def lookup(self, key: type[_T]) -> Binding[_T]:
        """Return binding registered for given type or raise a BindingNotFoundError."""
        binding = self._registry.get_binding(key)
        if binding is None:
            raise BindingNotFoundError(key)
        return binding

    def register(self, type_: type[_T]) -> Binder[_T]:
        return Binder(self._registry, type_)

    @overload
    def provider(self, factory: _U) -> _U: ...

    @overload
    def provider(
        self, *, enter: bool = ..., lifetime: Lifetime = ...
    ) -> Callable[[_U], _U]: ...

    def provider(
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


class Scope(Releasable["Scope"]):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self.container = container
        self._registry = Registry()
        self._logger = logging.getLogger(__name__)

        self.container.on_release(self.release)

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
        return self._registry.get_binding(type_) or self.container.lookup(type_)
