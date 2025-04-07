import logging
import warnings
from inspect import isgeneratorfunction
from types import FunctionType, LambdaType, MethodType
from typing import Callable, TypeVar, get_args, overload

from typing_extensions import Any, Self

from handless._container import Container
from handless._provider import (
    Lifetime,
    Provider,
    ProviderFactoryIn,
    ProviderLambdaFactory,
)
from handless._utils import default, get_return_type
from handless.exceptions import ProviderNotFoundError

_T = TypeVar("_T")
_U = TypeVar("_U", bound=ProviderFactoryIn[..., Any])


class Registry:
    def __init__(self, autobind: bool = True) -> None:
        self._autobind = autobind
        self._bindings: dict[type, Provider[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def __contains__(self, key: object) -> bool:
        return key in self._bindings

    def __getitem__(self, key: type[_T]) -> Provider[_T]:
        if key not in self:
            if not self._autobind:
                raise ProviderNotFoundError(key)
            self.register(key)
        return self._bindings[key]

    def __setitem__(self, key: type[_T], provider: Provider[_T]) -> None:
        is_overwrite = key in self
        self._bindings[key] = provider
        self._logger.info(
            "Registered %s%s: %s", key, " (overwrite)" if is_overwrite else "", provider
        )

    def register(
        self,
        type_: type[_T],
        provider: _T | type[_T] | ProviderLambdaFactory[_T] | None = None,
        lifetime: Lifetime | None = None,
        enter: bool | None = None,
    ) -> Self:
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
                return self._register_lambda_factory(
                    type_, provider, enter=enter, lifetime=lifetime
                )
            case _:
                return self._register_value(
                    type_, provider, enter=enter, lifetime=lifetime
                )

    def _register_value(
        self, type_: type[Any], value: Any, enter: bool | None = None, **kwargs: Any
    ) -> Self:
        if kwargs:
            warnings.warn(
                f"Passing {', '.join(kwargs)} keyword argument(s) has no effect when "
                "an object is given.",
                stacklevel=3,
            )
        return self._register(
            type_, Provider.for_value(value, enter=default(enter, False))
        )

    def _register_factory(
        self,
        type_: type[_T],
        factory: ProviderFactoryIn[..., _T] | None = None,
        enter: bool | None = None,
        lifetime: Lifetime | None = None,
    ) -> Self:
        return self._register(
            type_,
            Provider.for_factory(
                factory or type_,
                enter=default(enter, True),
                lifetime=lifetime or "transient",
            ),
        )

    def _register_lambda_factory(
        self,
        type_: type[_T],
        factory: ProviderLambdaFactory[_T],
        enter: bool | None = None,
        lifetime: Lifetime | None = None,
    ) -> Self:
        return self._register(
            type_,
            Provider.for_lambda_factory(
                factory, enter=default(enter, True), lifetime=lifetime or "transient"
            ),
        )

    def _register_alias(
        self, type_: type[Any], alias: type[Any], **kwargs: Any
    ) -> Self:
        if kwargs:
            warnings.warn(
                f"Passing {', '.join(kwargs)} keyword argument(s) has no effect when a type"
                " is given.",
                stacklevel=3,
            )
        return self._register(type_, Provider.for_alias(alias))

    def _register(self, type_: type[_T], provider: Provider[_T]) -> Self:
        self[type_] = provider
        return self

    @overload
    def provider(
        self, *, lifetime: Lifetime = ..., enter: bool = ...
    ) -> Callable[[_U], _U]: ...

    @overload
    def provider(self, factory: _U) -> _U: ...

    def provider(
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
            if isgeneratorfunction(factory):
                rettype = get_args(rettype)[0]
            if not rettype:
                raise TypeError(f"{factory} has no return type annotation")
            self._register_factory(rettype, factory, lifetime=lifetime, enter=enter)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    def create_container(self) -> Container:
        """Create and return a new container using this registry."""
        return Container(self)
