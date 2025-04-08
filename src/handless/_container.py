import logging
import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TYPE_CHECKING, Any, TypeVar, cast

from handless._binding import Binding
from handless.exceptions import ResolveError

if TYPE_CHECKING:
    from handless._registry import Registry


_T = TypeVar("_T")


class Container:
    def __init__(self, registry: "Registry") -> None:
        self._registry = registry
        self._cache: dict[type[Any], Any] = {}
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
            return binding.lifetime.accept(self, binding)
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
        if binding.type_ not in self._cache:
            self._cache[binding.type_] = self._get_instance(binding)
        return cast(_T, self._cache[binding.type_])

    def _get_instance(self, binding: Binding[_T]) -> _T:
        instance = binding.provider(self)
        if isinstance(instance, AbstractContextManager) and binding.enter:
            instance = self._exit_stack.enter_context(instance)
        # TODO: if enter is False but instance is a context manager and NOT an instance
        # of binding type, we must enter anyway. Maybe we should handle this at typing
        # level instead
        with suppress(TypeError):
            if not isinstance(instance, binding.type_):
                warnings.warn(
                    f"Container resolved {binding.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    RuntimeWarning,
                )
        return instance


class ScopedContainer(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry)
        self._parent = parent
        self._logger = logging.getLogger(f"{__name__}.scope")

    def _resolve_singleton(self, binding: Binding[_T]) -> _T:
        return self._parent._resolve_singleton(binding)

    def _resolve_scoped(self, binding: Binding[_T]) -> _T:
        return self._get_cached_instance(binding)
