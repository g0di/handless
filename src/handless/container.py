import logging
from contextlib import AbstractContextManager, ExitStack
from inspect import Parameter, isclass
from typing import TypeVar, cast, overload

from typing_extensions import TYPE_CHECKING, Any

from handless.descriptor import (
    AliasServiceDescriptor,
    FactoryServiceDescriptor,
    ServiceDescriptor,
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

    def create_scope(self) -> "ScopedContainer":
        return ScopedContainer(self)

    def clear(self) -> None:
        self._cache.clear()

    def __getitem__(self, type_: type[_T]) -> _T:
        return self.resolve(type_)

    @overload
    def resolve(self, type_: type[_T]) -> _T: ...

    @overload
    def resolve(self, type_: type[Any]) -> Any: ...

    def resolve(self, type_: type[_T]) -> _T:
        if isclass(type_) and issubclass(type_, Container):
            # NOTE: When receiving lambda parameter, just return the container
            return cast(_T, self)

        descriptor = self._get_descriptor(type_)
        try:
            return descriptor.accept(self)
        except Exception as error:
            raise ServiceResolveError(type_, str(error)) from error
        finally:
            self._logger.info(
                "Resolved %s%s: %s",
                type_,
                " (unregistered)" if type_ in self._registry else "",
                descriptor,
            )

    def _get_descriptor(self, type_: type[_T]) -> ServiceDescriptor[_T]:
        descriptor = self._registry.get_descriptor(type_)
        if descriptor is None:
            if self._strict:
                raise ServiceNotFoundError(type_)
            return FactoryServiceDescriptor(type_)
        return descriptor

    def _resolve_value(self, descriptor: ValueServiceDescriptor[_T]) -> _T:
        if descriptor.enter and isinstance(descriptor.value, AbstractContextManager):
            return cast(_T, descriptor.value.__enter__())
        return descriptor.value

    def _resolve_alias(self, descriptor: AliasServiceDescriptor[_T]) -> _T:
        return self.resolve(descriptor.alias)

    def _resolve_transient(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor)

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_cached_instance(descriptor)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        raise ValueError("Can not resolve scoped service outside a scope")

    def _get_cached_instance(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        if descriptor not in self._cache:
            self._cache[descriptor] = self._get_instance(descriptor)
        return cast(_T, self._cache[descriptor])

    def _get_instance(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        args = {
            # NOTE: pass the container when the parameter is empty
            # This happens when resolving a lambda function
            pname: (
                self.resolve(ptype.annotation)
                if ptype.annotation != Parameter.empty
                else self
            )
            for pname, ptype in descriptor.params.items()
        }
        instance = descriptor.factory(**args)
        if isinstance(instance, AbstractContextManager):
            return instance.__enter__()
        return instance


class ScopedContainer(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry, strict=parent._strict)
        self._parent = parent
        self._logger = logging.getLogger(f"{__name__}.scope")

    def _resolve_singleton(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._parent._resolve_singleton(descriptor)

    def _resolve_scoped(self, descriptor: FactoryServiceDescriptor[_T]) -> _T:
        return self._get_cached_instance(descriptor)
