from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, _GeneratorContextManager, contextmanager
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, get_args, overload

from handless._registrations import Registration, RegistrationBuilder
from handless._utils import get_return_type, iscontextmanager
from handless.containers import Container
from handless.exceptions import (
    RegistrationAlreadyExistingError,
    RegistrationNotFoundError,
)

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
    def __init__(
        self, *, autobind: bool = True, allow_direct_overrides: bool = False
    ) -> None:
        """Create a new registry.

        :param autobind: If True, registry will register automatically unregistered
            requested types on the fly, defaults to True.
        :param allow_direct_overrides: If True registry will allow overriding a previously
            registered type, defaults to False
        """
        self._autobind = autobind
        self._allow_direct_overrides = allow_direct_overrides
        self._registrations: dict[type[Any], Registration[Any]] = {}
        self._logger = logging.getLogger(__name__)
        self._overrides: Registry | None = None

    def __contains__(self, key: object) -> bool:
        return key in self._registrations

    def __setitem__(self, key: type[_T], registration: Registration[_T]) -> None:
        if not self._allow_direct_overrides and registration.type_ in self:
            raise RegistrationAlreadyExistingError(registration.type_)
        is_overwrite = registration.type_ in self
        self._registrations[key] = registration
        self._logger.info(
            "Registered %s%s: %s",
            registration.type_,
            " (overwrite)" if is_overwrite else "",
            registration,
        )

    def __getitem__(self, key: type[_T]) -> Registration[_T]:
        return self._registrations[key]

    @contextmanager
    def override(self) -> Iterator[Registry]:
        self._overrides = Registry(autobind=False, allow_direct_overrides=False)
        try:
            yield self._overrides
        finally:
            self._overrides = None

    def create_container(self) -> Container:
        """Create and return a new container using this registry."""
        return Container(self)

    def lookup(self, key: type[_T]) -> Registration[_T]:
        if self._overrides and key in self._overrides:
            return self._overrides.lookup(key)
        if key not in self:
            if not self._autobind:
                raise RegistrationNotFoundError(key)
            self.register(key).self()
        return self[key]

    def register(self, type_: type[_T]) -> RegistrationBuilder[_T]:
        return RegistrationBuilder(self, type_)

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
            self.register(rettype).factory(factory, lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper
