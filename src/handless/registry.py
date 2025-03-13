import logging
from inspect import isclass
from types import EllipsisType
from typing import Callable, TypeVar, overload

from typing_extensions import Any, ParamSpec, Self

from handless._utils import get_return_type
from handless.container import Container
from handless.descriptor import (
    Alias,
    Factory,
    Lifetime,
    Scoped,
    ServiceDescriptor,
    ServiceFactory,
    Singleton,
    Value,
)
from handless.exceptions import RegistrationError

_P = ParamSpec("_P")
_T = TypeVar("_T")


class Registry:
    def __init__(self) -> None:
        self._services: dict[type, ServiceDescriptor[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def get_descriptor(self, type_: type[_T]) -> ServiceDescriptor[_T] | None:
        """Get descriptor registered for given service type, if any or None."""
        return self._services.get(type_)

    def create_container(self, *, strict: bool = False) -> Container:
        """Create and return a new container using this registry."""
        return Container(self, strict=strict)

    ###########################
    # Imperative registration #
    ###########################

    def __contains__(self, type_: type[_T]) -> bool:
        return type_ in self._services

    def __setitem__(
        self,
        type_: type[_T],
        descriptor: ServiceDescriptor[_T] | _T | ServiceFactory[_T] | EllipsisType,
    ) -> None:
        _service_descriptor = None if descriptor is ... else descriptor
        self.register(type_, _service_descriptor)

    @overload
    def register(
        self,
        type_: type[_T],
        descriptor: ServiceDescriptor[_T] | _T | None = ...,
    ) -> Self: ...

    @overload
    def register(
        self,
        type_: type[_T],
        descriptor: ServiceFactory[_T] | None = ...,
        lifetime: Lifetime = ...,
    ) -> Self: ...

    def register(
        self,
        type_: type[_T],
        descriptor: ServiceDescriptor[_T] | _T | ServiceFactory[_T] | None = None,
        lifetime: Lifetime = "transient",
    ) -> Self:
        """Register a descriptor for resolving the given type.

        :param type_: Type of the service to register
        :param service_descriptor: A ServiceDescriptor, a callable or any other value
        :param lifetime: The lifetime of the descriptor to register
        """
        if isinstance(descriptor, ServiceDescriptor):
            return self._register(type_, descriptor)
        if isclass(descriptor):
            return self.register_alias(type_, descriptor)
        if descriptor is None or callable(descriptor):
            return self.register_factory(type_, descriptor, lifetime=lifetime)
        return self.register_value(type_, descriptor)

    def register_value(
        self, type_: type[_T], service_value: _T, *, enter: bool = False
    ) -> Self:
        """Registers given value to be returned when resolving given service type.

        :param type_: Type of the service to register
        :param service_value: Service value
        """
        return self._register(type_, Value(service_value, enter=enter))

    def register_factory(
        self,
        type_: type[_T],
        factory: ServiceFactory[_T] | None = None,
        lifetime: Lifetime = "transient",
    ) -> Self:
        """Registers given callable to be called to resolve the given type.

        Lifetime is transient by default meaning the factory will be executed on each
        resolve.
        """
        return self._register(type_, Factory(factory or type_, lifetime=lifetime))

    def register_singleton(
        self, type_: type[_T], factory: ServiceFactory[_T] | None = None
    ) -> Self:
        """Registers given callable to be called once when resolving given service type."""
        return self._register(type_, Singleton(factory or type_))

    def register_scoped(
        self, type_: type[_T], factory: ServiceFactory[_T] | None = None
    ) -> Self:
        """Registers given callable to be called once per scope when resolving given service type."""
        return self._register(type_, Scoped(factory or type_))

    def register_alias(self, type_: type[_T], alias: type[_T]) -> Self:
        """Registers given registered type to be used when resolving given service type."""
        # NOTE: ensure given impl type is a subclass of service type because
        # mypy currently allows passing any classes to impl
        if not isclass(alias) or not issubclass(alias, type_):
            raise RegistrationError(f"{alias} is not a subclass of {type_}")
        return self._register(type_, Alias(alias))

    # Low level API
    def _register(
        self, type_: type[_T], service_descriptor: ServiceDescriptor[_T]
    ) -> Self:
        self._services[type_] = service_descriptor
        self._logger.info("Registered %s: %s", type_, service_descriptor)
        return self

    ############################
    # Declarative registration #
    ############################

    # Factory decorator

    @overload
    def factory(
        self,
        *,
        lifetime: Lifetime = ...,
    ) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def factory(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def factory(
        self,
        factory: Callable[_P, _T] | None = None,
        *,
        lifetime: Lifetime = "transient",
    ) -> Any:
        def wrapper(factory: Callable[_P, _T]) -> Callable[_P, _T]:
            rettype = get_return_type(factory)
            if not rettype:
                raise RegistrationError(f"{factory} has no return type annotation")
            self.register_factory(rettype, factory, lifetime=lifetime)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    # Singleton decorator

    @overload
    def singleton(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def singleton(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def singleton(self, factory: Callable[_P, _T] | None = None) -> Any:
        return self.factory(factory, lifetime="singleton")  # type: ignore[call-overload]

    # Scoped decorator

    @overload
    def scoped(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def scoped(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def scoped(self, factory: Callable[_P, _T] | None = None) -> Any:
        return self.factory(factory, lifetime="scoped")  # type: ignore[call-overload]
