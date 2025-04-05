import logging
from typing import Callable, Iterator, TypeVar, overload

from typing_extensions import Any, ParamSpec, Self

from handless._container import Container
from handless._descriptor import Lifetime, ServiceDescriptor, ServiceDescriptorFactoryIn
from handless._utils import get_return_type
from handless.exceptions import RegistrationError

_P = ParamSpec("_P")
_T = TypeVar("_T")


class Registry:
    def __init__(self, autobind: bool = True) -> None:
        self._autobind = autobind
        self._services: dict[type, ServiceDescriptor[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def __contains__(self, key: object) -> bool:
        return key in self._services

    def __getitem__(self, key: type[_T]) -> ServiceDescriptor[_T]:
        return self._services[key]

    def __delitem__(self, key: type[Any]) -> None:
        del self._services[key]

    def __iter__(self) -> Iterator[type[Any]]:
        return iter(self._services)

    def __len__(self) -> int:
        return len(self._services)

    def __setitem__(self, key: type[_T], descriptor: ServiceDescriptor[_T]) -> None:
        self._services[key] = descriptor
        self._logger.info("Registered %s: %s", key, descriptor)

    def get(self, type_: type[_T]) -> ServiceDescriptor[_T] | None:
        """Get descriptor registered for given service type, if any or None."""
        if type_ not in self and self._autobind:
            self[type_] = ServiceDescriptor(type_)
        return self._services.get(type_)

    def create_container(self) -> Container:
        """Create and return a new container using this registry."""
        return Container(self)

    def register(self, type_: type[_T], descriptor: ServiceDescriptor[_T]) -> Self:
        self._services[type_] = descriptor
        return self

    def register_factory(
        self,
        type_: type[_T],
        factory: ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        lifetime: Lifetime = "transient",
        enter: bool = True,
    ) -> Self:
        """Registers given callable to be called to resolve the given type.

        Lifetime is transient by default meaning the factory will be executed on each
        resolve.
        """
        return self.register(
            type_,
            ServiceDescriptor.for_factory(
                factory or type_, lifetime=lifetime, enter=enter
            ),
        )

    def register_singleton(
        self,
        type_: type[_T],
        singleton: _T | ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        enter: bool | None = None,
    ) -> Self:
        """_summary_

        Caveat: If you want to register a callable object as a singleton directly you
        must wrap it into a lambda. Otherwise, the registration will consider it as a
        factory and will call your object at resolve type instead of returning it.

        :param type_: _description_
        :param singleton: _description_, defaults to None
        :param enter: _description_, defaults to None
        :return: _description_
        """
        descriptor = (
            ServiceDescriptor.for_factory(
                singleton or type_,
                enter=True if enter is None else enter,
                lifetime="singleton",
            )
            if singleton is None or callable(singleton)
            else ServiceDescriptor.for_instance(
                singleton, enter=False if enter is None else enter
            )
        )
        return self.register(type_, descriptor)

    def register_scoped(
        self,
        type_: type[_T],
        factory: ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        enter: bool = True,
    ) -> Self:
        """Registers given callable to be called once per scope when resolving given service type."""
        return self.register(
            type_,
            ServiceDescriptor.for_factory(
                factory or type_, enter=enter, lifetime="scoped"
            ),
        )

    def register_implementation(self, type_: type[Any], alias: type[Any]) -> Self:
        """Registers given registered type to be used when resolving given service type."""
        return self.register(type_, ServiceDescriptor.for_implementation(alias))

    ############################
    # Declarative registration #
    ############################

    # Factory decorator

    @overload
    def factory(
        self, *, lifetime: Lifetime = ...
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
