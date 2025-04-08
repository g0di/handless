import logging
import warnings
from contextlib import AbstractContextManager, _GeneratorContextManager
from inspect import isgeneratorfunction
from types import FunctionType, LambdaType, MethodType
from typing import Any, Callable, Iterator, ParamSpec, TypeVar, get_args, overload

from handless import _lifetime
from handless._binding import Binding
from handless._container import Container
from handless._lifetime import Lifetime
from handless._provider import (
    AliasProvider,
    FactoryProvider,
    LambdaProvider,
    ValueProvider,
)
from handless._utils import (
    count_func_params,
    default,
    get_return_type,
    iscontextmanager,
)
from handless.exceptions import BindingNotFoundError

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
    def __init__(self, autobind: bool = True) -> None:
        self._autobind = autobind
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
        lifetime: Lifetime | None = None,
        enter: bool | None = None,
    ) -> "Registry":
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
                return self._register_alias(
                    type_, provider, lifetime=lifetime, enter=enter
                )
            case None:
                return self._register_factory(
                    type_, provider, enter=enter, lifetime=lifetime
                )
            case FunctionType() | MethodType() | LambdaType():
                if count_func_params(provider) == 1:
                    return self._register_lambda(
                        type_, provider, enter=enter, lifetime=lifetime
                    )
                return self._register_factory(
                    type_, provider, enter=enter, lifetime=lifetime
                )
            case _:
                return self._register_value(
                    type_, provider, enter=enter, lifetime=lifetime
                )

    @overload
    def binding(self, factory: _U) -> _U: ...

    @overload
    def binding(
        self, *, lifetime: Lifetime = ..., enter: bool = ...
    ) -> Callable[[_U], _U]: ...

    def binding(
        self,
        factory: _U | None = None,
        *,
        lifetime: Lifetime = "transient",
        enter: bool = True,
    ) -> Any:
        """Register decorated function as factory provider for its return type annotation

        :param factory: The decorated factory function, defaults to None
        :param lifetime: The factory lifetime, defaults to "transient"
        :return: The pristine function
        """

        def wrapper(factory: _U) -> _U:
            rettype = get_return_type(factory)
            if isgeneratorfunction(factory) or iscontextmanager(factory):
                rettype = get_args(rettype)[0]
            if not rettype:
                raise TypeError(f"{factory} has no return type annotation")
            self._register_factory(rettype, factory, lifetime=lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def _register_value(
        self, type_: type[Any], value: Any, enter: bool | None = None, **kwargs: Any
    ) -> "Registry":
        if kwargs:
            warnings.warn(
                f"Passing {', '.join(kwargs)} keyword argument(s) has no effect when "
                "an object is given.",
                stacklevel=3,
            )
        return self._register(
            Binding(
                type_,
                ValueProvider(value),
                enter=default(enter, False),
                lifetime=_lifetime.SingletonLifetime(),
            )
        )

    def _register_factory(
        self,
        type_: type[_T],
        factory: _Factory[..., _T] | None = None,
        enter: bool | None = None,
        lifetime: Lifetime | None = None,
    ) -> "Registry":
        return self._register(
            Binding(
                type_,
                FactoryProvider(factory or type_),
                enter=default(enter, True),
                lifetime=_lifetime.parse(lifetime or "transient"),
            )
        )

    def _register_lambda(
        self,
        type_: type[_T],
        factory: _LambdaFactory[_T],
        enter: bool | None = None,
        lifetime: Lifetime | None = None,
    ) -> "Registry":
        return self._register(
            Binding(
                type_,
                LambdaProvider(factory),
                enter=default(enter, True),
                lifetime=_lifetime.parse(lifetime or "transient"),
            )
        )

    def _register_alias(
        self, type_: type[Any], alias_type: type[Any], **kwargs: Any
    ) -> "Registry":
        if kwargs:
            warnings.warn(
                f"Passing {', '.join(kwargs)} keyword argument(s) has no effect when a type"
                " is given.",
                stacklevel=3,
            )
        return self._register(Binding(type_, AliasProvider(alias_type), enter=False))

    def _register(self, binding: Binding[Any]) -> "Registry":
        is_overwrite = binding.type_ in self
        self._bindings[binding.type_] = binding
        self._logger.info(
            "Registered %s%s: %s",
            binding.type_,
            " (overwrite)" if is_overwrite else "",
            binding,
        )
        return self
