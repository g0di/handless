from inspect import isclass
from typing import Callable, TypeVar, overload

from typing_extensions import Any, ParamSpec, Self

from handless.container import Container
from handless.descriptor import (
    Factory,
    Lifetime,
    ServiceDescriptor,
    as_factory,
    as_impl,
    as_scoped,
    as_singleton,
    as_value,
    get_return_type,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")
_U = TypeVar("_U", bound=type[_T])


class RegistryException(Exception):
    pass


class MissingReturnTypeAnnotationError(RegistryException):
    pass


class Registry:
    def __init__(self) -> None:
        self._services: dict[type, ServiceDescriptor[Any]] = {}

    def get_descriptor(self, service_type: type[_T]) -> ServiceDescriptor[_T] | None:
        """Get descriptor registered for given service type, if any or None."""
        return self._services.get(service_type)

    def create_container(self) -> "Container":
        """Create and return a new container using this registry."""
        return Container(self)

    ###########################
    # Imperative registration #
    ###########################

    def __setitem__(
        self,
        service_type: type[_T],
        service_descriptor: ServiceDescriptor[_T] | _T | Factory[_T],
    ) -> None:
        self.register(service_type, service_descriptor)

    @overload
    def register(
        self,
        service_type: type[_T],
        service_descriptor: ServiceDescriptor[_T] | _T | None = ...,
    ) -> Self: ...

    @overload
    def register(
        self,
        service_type: type[_T],
        service_descriptor: Factory[_T] | None = ...,
        lifetime: Lifetime | None = ...,
    ) -> Self: ...

    def register(
        self,
        service_type: type[_T],
        service_descriptor: ServiceDescriptor[_T] | _T | Factory[_T] | None = None,
        lifetime: Lifetime | None = None,
    ) -> Self:
        """Register a descriptor for resolving the given type.

        :param service_type: Type of the service to register
        :param service_descriptor: A ServiceDescriptor, a callable or any other value
        :param lifetime: The lifetime of the descriptor to register
        """
        if isinstance(service_descriptor, ServiceDescriptor):
            return self._register(service_type, service_descriptor)
        if isclass(service_descriptor):
            return self.register_impl(service_type, service_descriptor)
        if service_descriptor is None or callable(service_descriptor):
            return self.register_factory(
                service_type, service_descriptor, lifetime=lifetime
            )
        return self.register_value(service_type, service_descriptor)

    def register_value(self, service_type: type[_T], service_value: _T) -> Self:
        """Registers given value to be returned when resolving given service type.

        :param service_type: Type of the service to register
        :param service_value: Service value
        """
        return self._register(service_type, as_value(service_value))

    def register_factory(
        self,
        service_type: type[_T],
        service_factory: Factory[_T] | None = None,
        lifetime: Lifetime | None = None,
    ) -> Self:
        """Registers given callable to be called each time when resolving given service type."""
        return self._register(
            service_type, as_factory(service_factory or service_type, lifetime)
        )

    def register_singleton(
        self, service_type: type[_T], service_factory: Factory[_T] | None = None
    ) -> Self:
        """Registers given callable to be called once when resolving given service type."""
        return self._register(
            service_type, as_singleton(service_factory or service_type)
        )

    def register_scoped(
        self, service_type: type[_T], service_factory: Factory[_T] | None = None
    ) -> Self:
        """Registers given callable to be called once per scope when resolving given service type."""
        return self._register(service_type, as_scoped(service_factory or service_type))

    def register_impl(self, service_type: type[_T], service_impl: type[_T]) -> Self:
        """Registers given registered type to be used when resolving given service type."""
        # NOTE: ensure given impl type is a subclass of service type because
        # mypy currently allows passing any classes to impl
        if not isclass(service_impl) or not issubclass(service_impl, service_type):
            raise TypeError(f"{service_impl} is not a subclass of {service_type}")
        return self._register(service_type, as_impl(service_impl))

    # Low level API
    def _register(
        self, service_type: type[_T], service_descriptor: ServiceDescriptor[_T]
    ) -> Self:
        self._services[service_type] = service_descriptor
        return self

    ############################
    # Declarative registration #
    ############################

    @overload
    def factory(
        self, lifetime: Lifetime | None = None
    ) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def factory(self, service_factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def factory(
        self,
        service_factory: Callable[_P, _T] | None = None,
        lifetime: Lifetime | None = None,
    ) -> Any:
        def wrapper(service_factory: Callable[_P, _T]) -> Callable[_P, _T]:
            try:
                rettype = get_return_type(service_factory)
            except ValueError as error:
                msg = f"Can not register service type {service_factory}: {error}"
                raise MissingReturnTypeAnnotationError(msg)
            else:
                self.register_factory(rettype, service_factory, lifetime=lifetime)
                # NOTE: return decorated func untouched to ease reuse
                return service_factory

        if service_factory is not None:
            return wrapper(service_factory)
        return wrapper

    # Singleton decorator

    @overload
    def singleton(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def singleton(self, service_factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def singleton(self, service_factory: Callable[_P, _T] | None = None) -> Any:
        return self.factory(service_factory, lifetime="singleton")

    # Scoped decorator

    @overload
    def scoped(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def scoped(self, service_factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def scoped(self, service_factory: Callable[_P, _T] | None = None) -> Any:
        return self.factory(service_factory, lifetime="scoped")
