import logging
from contextlib import AbstractContextManager, ExitStack
from inspect import Parameter
from typing import TypeVar, cast

from typing_extensions import TYPE_CHECKING, Any

from handless.descriptor import (
    AliasServiceDescriptor,
    FactoryServiceDescriptor,
    ValueServiceDescriptor,
)
from handless.exceptions import ServiceNotFoundError, ServiceResolveError

if TYPE_CHECKING:
    from handless.registry import Registry


_T = TypeVar("_T")


class Container:
    def __init__(self, registry: "Registry", *, strict: bool = False) -> None:
        self._strict = strict
        self._registry = registry
        self._cache: dict[FactoryServiceDescriptor[Any], Any] = {}
        self._exit_stack = ExitStack()
        self._logger = logging.getLogger(__name__)

    def resolve(self, type_: type[_T]) -> _T:
        if issubclass(type_, (Parameter, Container)):
            # NOTE: When receiving lambda parameter, just return the container
            return cast(_T, self)

        descriptor = self._registry.get_descriptor(type_)
        if descriptor is None:
            if self._strict:
                raise ServiceNotFoundError(type_)
            descriptor = FactoryServiceDescriptor(type_)

        try:
            if isinstance(descriptor, ValueServiceDescriptor):
                return descriptor.value
            if isinstance(descriptor, AliasServiceDescriptor):
                return self.resolve(descriptor.alias)
            if isinstance(descriptor, FactoryServiceDescriptor):
                return self._resolve_factory(descriptor)
            raise NotImplementedError("Unhandled descriptor {descriptor}")
        except Exception as error:
            raise ServiceResolveError(type_, str(error)) from error

    def _resolve_factory(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        if descriptor.lifetime == "scoped":
            return self._resolve_scoped(descriptor)
        if descriptor.lifetime == "singleton":
            return self._resolve_singleton(descriptor)
        return self._resolve_transient(descriptor)

    def _resolve_transient(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=False)

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=True)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        raise ValueError("Can not resolve scoped service outside a scope")

    def _get_instance(
        self, descriptor: FactoryServiceDescriptor[_T], *, cached: bool
    ) -> _T:
        if not cached:
            instance = descriptor.get_instance(self)
            if isinstance(instance, AbstractContextManager):
                return self._exit_stack.enter_context(instance)
            return instance

        if descriptor not in self._cache:
            self._cache[descriptor] = self._get_instance(descriptor, cached=False)
        return cast(_T, self._cache[descriptor])

    def create_scope(self) -> "ScopedContainer":
        return ScopedContainer(self)


class ScopedContainer(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry, strict=parent._strict)
        self._parent = parent

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._parent._resolve_singleton(descriptor)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor, cached=True)
