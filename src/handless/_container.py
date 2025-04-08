import logging
import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TypeVar, cast

from typing_extensions import TYPE_CHECKING, Any

from handless._binding import Binding
from handless.exceptions import ResolveError

if TYPE_CHECKING:
    from handless._registry import Registry


_T = TypeVar("_T")


class Container:
    def __init__(self, registry: "Registry") -> None:
        self._registry = registry
        self._cache: dict[Binding[Any], Any] = {}
        self._exit_stack = ExitStack()
        self._logger = logging.getLogger(__name__)

    def create_scope(self) -> "ScopedContainer":
        return ScopedContainer(self)

    def close(self) -> None:
        self._exit_stack.close()
        self._cache.clear()

    def resolve(self, type_: type[_T]) -> _T:
        if issubclass(type_, Container):
            return cast(_T, self)

        binding = self._registry.lookup(type_)

        try:
            if binding.lifetime == "scoped":
                instance = self._resolve_scoped(binding)
            elif binding.lifetime == "singleton":
                instance = self._resolve_singleton(binding)
            else:
                instance = self._resolve_transient(binding)
            with suppress(TypeError):
                if not isinstance(instance, type_):
                    warnings.warn(
                        f"Container resolved {type_} with {instance} which is not an instance of this type. "
                        "This could lead to unexpected errors.",
                        RuntimeWarning,
                    )
            return instance
        except Exception as error:
            raise ResolveError(type_) from error
        finally:
            self._logger.info(
                "Resolved %s%s: %s",
                type_,
                " (unregistered)" if type_ in self._registry else "",
                binding,
            )

    def _resolve_transient(self, binding: Binding[_T]) -> _T:
        return self._get_instance(binding)

    def _resolve_singleton(self, binding: Binding[_T]) -> _T:
        return self._get_cached_instance(binding)

    def _resolve_scoped(self, binding: Binding[_T]) -> _T:
        raise ValueError("Can not resolve scoped type outside a scope")

    def _get_cached_instance(self, binding: Binding[_T]) -> _T:
        if binding not in self._cache:
            self._cache[binding] = self._get_instance(binding)
        return cast(_T, self._cache[binding])

    def _get_instance(self, binding: Binding[_T]) -> _T:
        args = {param.name: self.resolve(param.annotation) for param in binding.params}
        instance = binding.provider(**args)
        if isinstance(instance, AbstractContextManager) and binding.enter:
            instance = self._exit_stack.enter_context(instance)
        return cast(_T, instance)


class ScopedContainer(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry)
        self._parent = parent
        self._logger = logging.getLogger(f"{__name__}.scope")

    def _resolve_singleton(self, binding: Binding[_T]) -> _T:
        return self._parent._resolve_singleton(binding)

    def _resolve_scoped(self, binding: Binding[_T]) -> _T:
        return self._get_cached_instance(binding)
