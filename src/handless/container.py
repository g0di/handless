from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, ExitStack
from inspect import isclass
from typing import TypeVar, cast

from typing_extensions import TYPE_CHECKING, Any

from handless.descriptor import AliasServiceDescriptor, FactoryServiceDescriptor

_T = TypeVar("_T")


if TYPE_CHECKING:
    from handless.registry import Registry


class ContainerException(Exception):
    pass


class ServiceNotFoundError(ContainerException):
    def __init__(self, service_type: type) -> None:
        super().__init__(f"There is no service {service_type} registered")


class ServiceResolveError(ContainerException):
    def __init__(self, service_type: type, reason: str) -> None:
        super().__init__(f"Failed resolving {service_type}: {reason}")


class BaseContainer(ABC):
    def __init__(self, registry: "Registry") -> None:
        self._registry = registry
        self._cache: dict[FactoryServiceDescriptor[Any], Any] = {}
        self._exit_stack = ExitStack()

    def resolve(self, service_type: type[_T] | str) -> _T:
        if service_type == "Container" or (
            isclass(service_type) and issubclass(service_type, BaseContainer)
        ):
            return self

        descriptor = self._registry.get_descriptor(service_type)
        if descriptor is None:
            raise ServiceNotFoundError(service_type)

        try:
            if isinstance(descriptor, AliasServiceDescriptor):
                return self._resolve_impl(descriptor)
            if descriptor.lifetime == "scoped":
                return self._resolve_scoped(descriptor)
            if descriptor.lifetime == "singleton":
                return self._resolve_singleton(descriptor)
            return self._resolve_transient(descriptor)
        except Exception as error:
            raise ServiceResolveError(service_type, str(error)) from error

    def _resolve_impl(self, descriptor: AliasServiceDescriptor[_T]) -> _T:
        return self.resolve(descriptor.impl)

    def _resolve_transient(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=False)

    @abstractmethod
    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        raise NotImplementedError

    @abstractmethod
    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        raise NotImplementedError

    def _get_instance(
        self, descriptor: FactoryServiceDescriptor[_T], *, cached: bool
    ) -> _T:
        if not cached:
            args: dict[str, Any] = {
                pname: self.resolve(ptype)
                for pname, ptype in descriptor.type_hints.items()
                if pname != "return"
            }
            instance = descriptor.factory(**args)
            if descriptor.enter and isinstance(instance, AbstractContextManager):
                return self._exit_stack.enter_context(instance)
            return instance

        if descriptor not in self._cache:
            self._cache[descriptor] = self._get_instance(descriptor, cached=False)
        return cast(_T, self._cache[descriptor])


class Container(BaseContainer):
    def create_scope(self) -> "ScopedContainer":
        return ScopedContainer(self._registry, self)

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=True)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        raise ValueError("Can not resolve scoped service outside a scope")


class ScopedContainer(BaseContainer):
    def __init__(self, registry: "Registry", parent: Container) -> None:
        super().__init__(registry)
        self._parent = parent

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._parent._resolve_singleton(descriptor)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=True)
