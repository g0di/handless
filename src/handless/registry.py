from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, _GeneratorContextManager
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast, get_args, overload

from handless._bindings import Binder, Binding
from handless._utils import get_return_type, iscontextmanager
from handless.containers import Container
from handless.exceptions import RegistrationAlreadyExistError, RegistrationNotFoundError

if TYPE_CHECKING:
    from handless._lifetimes import LifetimeLiteral

_T = TypeVar("_T")
_P = ParamSpec("_P")
_Factory = (
    Callable[_P, _T]
    | Callable[_P, Iterator[_T]]
    | Callable[_P, AbstractContextManager[_T]]
    | Callable[_P, _GeneratorContextManager[_T, Any, Any]]
)
_LambdaFactory = _Factory[[Container], _T]
_U = TypeVar("_U", bound=Callable[..., Any])


class Registry:
    def __init__(self, *, autobind: bool = True) -> None:
        """Create a new registry.

        :param autobind: If True, registry will register automatically unregistered
            requested types on the fly, defaults to True.
        :param allow_direct_overrides: If True registry will allow overriding a previously
            registered type, defaults to False
        """
        self._autobind = autobind
        self._registrations: dict[type[Any], Binding[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def __contains__(self, key: object) -> bool:
        return key in self._registrations

    def lookup(self, key: type[_T]) -> Binding[_T]:
        if key not in self:
            if not self._autobind:
                raise RegistrationNotFoundError(key)
            self.bind(key).to_self()
        return cast("Binding[_T]", self._registrations[key])

    def bind(self, type_: type[_T]) -> Binder[_T]:
        return Binder(self, type_)

    def register(self, registration: Binding[Any]) -> Registry:
        if registration.type_ in self:
            raise RegistrationAlreadyExistError(registration.type_)

        self._registrations[registration.type_] = registration
        self._logger.info("Registered %s: %s", registration.type_, registration)
        return self

    @overload
    def factory(self, factory: _U) -> _U: ...

    @overload
    def factory(
        self, *, enter: bool = ..., lifetime: LifetimeLiteral = ...
    ) -> Callable[[_U], _U]: ...

    def factory(
        self,
        factory: _U | None = None,
        *,
        enter: bool = True,
        lifetime: LifetimeLiteral = "transient",
    ) -> Any:
        """Register decorated function as factory provider for its return type annotation.

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
            self.bind(rettype).to_factory(factory, lifetime=lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def create_container(self) -> Container:
        """Create and return a new container using this registry."""
        return Container(self)
