from __future__ import annotations

import logging
import warnings
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, _GeneratorContextManager
from inspect import isgeneratorfunction
from types import FunctionType, LambdaType, MethodType
from typing import TYPE_CHECKING, Any, ParamSpec, TypedDict, TypeVar, get_args, overload

from typing_extensions import Unpack

from handless import _lifetime
from handless._binding import Binding
from handless._container import Container
from handless._provider import (
    AliasProvider,
    FactoryProvider,
    LambdaProvider,
    ValueProvider,
)
from handless._utils import count_func_params, get_return_type, iscontextmanager
from handless.exceptions import BindingAlreadyExistingError, BindingNotFoundError

if TYPE_CHECKING:
    from handless._lifetime import Lifetime

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


class _BindingOptions(TypedDict, total=False):
    lifetime: Lifetime
    enter: bool


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
        self._bindings: dict[type, Binding[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def __contains__(self, key: object) -> bool:
        return key in self._bindings

    def create_container(self) -> Container:
        """Create and return a new container using this registry."""
        return Container(self)

    def lookup(self, key: type[_T]) -> Binding[_T]:
        if key not in self:
            if not self._autobind:
                raise BindingNotFoundError(key)
            self.register(key)
        return self._bindings[key]

    def register(
        self,
        type_: type[_T],
        provider: _T | type[_T] | _LambdaFactory[_T] | _Factory[[], _T] | None = None,
        **options: Unpack[_BindingOptions],
    ) -> Registry:
        """Register a provider for given type.

        The type of given provider argument determines how the type will be resolved:
        - An object produces a singleton binding resolving to this value.
          `enter` defaults to False because the registry was not responsible of creating it.
        - A type produces an alias binding. It means that given type will be resolved
          by actually resolving the provided alias. `enter` and `lifetime` have no effect.
        - A function produces a factory binding. This factory will be called when resolving given type.
          Returned value might be cached accross resolve based on its lifetime:
          - `transient`: The value is not cached at all
          - `scoped`: The value is cached for a scoped container lifetime
          - `singleton`: The value is cached for the container lifetime
          For factories, `enter` defaults to True so if a context manager is returned,
          it will be entered automatically. The context manager is automatically exited
          by the container when the value is no longer used.
        - `None` produces a factory binding using the given type itself as the factory.
          All other information about factory bindings apply as well

        :param type_: The type to register
        :param provider: The provider to which bind the given type, defaults to None
        :param lifetime: Lifetime of the binding, if it applies, defaults to None
        :param enter: Whether or not to enter (and exit) context managers automatically
            if the given provider resolve with a context manager, defaults to None
        :return: The registry
        """
        match provider:
            case type():
                return self._register_alias(type_, provider, **options)
            case None:
                return self._register_factory(type_, provider, **options)
            case FunctionType() | MethodType() | LambdaType():
                if count_func_params(provider) == 1:
                    return self._register_lambda(type_, provider, **options)
                return self._register_factory(type_, provider, **options)
            case _:
                return self._register_value(type_, provider, **options)

    @overload
    def binding(self, factory: _U) -> _U: ...

    @overload
    def binding(self, **options: Unpack[_BindingOptions]) -> Callable[[_U], _U]: ...

    def binding(
        self, factory: _U | None = None, **options: Unpack[_BindingOptions]
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
            self._register_factory(rettype, factory, **options)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def _register_value(
        self, type_: type[Any], value: object, **options: Unpack[_BindingOptions]
    ) -> Registry:
        enter = options.pop("enter", False)
        if options:
            warnings.warn(
                f"Passing {', '.join(options)} keyword argument(s) has no effect when "
                "an object is given.",
                stacklevel=3,
            )
        return self._register(
            Binding(
                type_,
                ValueProvider(value),
                enter=enter,
                lifetime=_lifetime.parse("singleton"),
            )
        )

    def _register_factory(
        self,
        type_: type[_T],
        factory: _Factory[..., _T] | None = None,
        **options: Unpack[_BindingOptions],
    ) -> Registry:
        return self._register(
            Binding(
                type_,
                FactoryProvider(factory or type_),
                enter=options.get("enter", True),
                lifetime=_lifetime.parse(options.get("lifetime", "transient")),
            )
        )

    def _register_lambda(
        self,
        type_: type[_T],
        factory: _LambdaFactory[_T],
        **options: Unpack[_BindingOptions],
    ) -> Registry:
        return self._register(
            Binding(
                type_,
                LambdaProvider(factory),
                enter=options.get("enter", True),
                lifetime=_lifetime.parse(options.get("lifetime", "transient")),
            )
        )

    def _register_alias(
        self,
        type_: type[Any],
        alias_type: type[Any],
        **options: Unpack[_BindingOptions],
    ) -> Registry:
        if options:
            warnings.warn(
                f"Passing {', '.join(options)} keyword argument(s) has no effect when a type"
                " is given.",
                stacklevel=3,
            )
        return self._register(
            Binding(
                type_,
                AliasProvider(alias_type),
                lifetime=_lifetime.parse("transient"),
                enter=False,
            )
        )

    def _register(self, binding: Binding[Any]) -> Registry:
        if not self._allow_direct_overrides and binding.type_ in self:
            raise BindingAlreadyExistingError(binding.type_)
        is_overwrite = binding.type_ in self
        self._bindings[binding.type_] = binding
        self._logger.info(
            "Registered %s%s: %s",
            binding.type_,
            " (overwrite)" if is_overwrite else "",
            binding,
        )
        return self
