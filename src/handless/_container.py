import logging
import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TypeVar, cast

from typing_extensions import TYPE_CHECKING, Any

from handless._descriptor import ServiceDescriptor
from handless.exceptions import ServiceNotFoundError, ServiceResolveError

if TYPE_CHECKING:
    from handless._registry import Registry


_T = TypeVar("_T")


class Container:
    def __init__(self, registry: "Registry") -> None:
        self._registry = registry
        self._cache: dict[ServiceDescriptor[Any], Any] = {}
        self._exit_stack = ExitStack()
        self._logger = logging.getLogger(__name__)

    def create_scope(self) -> "ScopedContainer":
        return ScopedContainer(self)

    def close(self) -> None:
        self._exit_stack.close()
        self._cache.clear()

    def __getitem__(self, type_: type[_T]) -> _T:
        return self.resolve(type_)

    def resolve(self, type_: type[_T]) -> _T:
        if issubclass(type_, Container):
            return cast(_T, self)
        descriptor = self._get_descriptor(type_)

        try:
            if descriptor.lifetime == "scoped":
                instance = self._resolve_scoped(descriptor)
            elif descriptor.lifetime == "singleton":
                instance = self._resolve_singleton(descriptor)
            else:
                instance = self._resolve_transient(descriptor)
            with suppress(TypeError):
                if not isinstance(instance, type_):
                    warnings.warn(
                        f"Container resolved {type_} with {instance} which is not an instance of this type. "
                        "This could lead to unexpected results.",
                        RuntimeWarning,
                    )
            return instance
        except Exception as error:
            raise ServiceResolveError(type_) from error
        finally:
            self._logger.info(
                "Resolved %s%s: %s",
                type_,
                " (unregistered)" if type_ in self._registry else "",
                descriptor,
            )

    def _get_descriptor(self, type_: type[_T]) -> ServiceDescriptor[_T]:
        descriptor = self._registry.get(type_)
        if descriptor is None:
            raise ServiceNotFoundError(type_)
        return descriptor

    def _resolve_transient(self, descriptor: ServiceDescriptor[_T]) -> _T:
        return self._get_instance(descriptor)

    def _resolve_singleton(self, descriptor: ServiceDescriptor[_T]) -> _T:
        return self._get_cached_instance(descriptor)

    def _resolve_scoped(self, descriptor: ServiceDescriptor[_T]) -> _T:
        raise ValueError("Can not resolve scoped service outside a scope")

    def _get_cached_instance(self, descriptor: ServiceDescriptor[_T]) -> _T:
        if descriptor not in self._cache:
            self._cache[descriptor] = self._get_instance(descriptor)
        return cast(_T, self._cache[descriptor])

    def _get_instance(self, descriptor: ServiceDescriptor[_T]) -> _T:
        args = {
            param.name: self.resolve(param.annotation) for param in descriptor.params
        }
        instance = descriptor.factory(**args)
        if isinstance(instance, AbstractContextManager) and descriptor.enter:
            instance = self._exit_stack.enter_context(instance)
        # NOTE: we blindly trust and return the instance. There is no point in raising an
        # error here.
        # TODO: maybe send a dev warning if instance if not an instance of requested type
        return cast(_T, instance)


class ScopedContainer(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry)
        self._parent = parent
        self._logger = logging.getLogger(f"{__name__}.scope")

    def _resolve_singleton(self, descriptor: ServiceDescriptor[_T]) -> _T:
        return self._parent._resolve_singleton(descriptor)

    def _resolve_scoped(self, descriptor: ServiceDescriptor[_T]) -> _T:
        return self._get_cached_instance(descriptor)
