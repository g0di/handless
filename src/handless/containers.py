from __future__ import annotations

import logging
import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TYPE_CHECKING, Any, TypeVar, cast

from typing_extensions import Self

from handless.exceptions import ResolveError

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.registry import Registry


_T = TypeVar("_T")


class Container(AbstractContextManager["Container"]):
    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._cache: dict[type[Any], Any] = {}
        self._exit_stack = ExitStack()
        self._logger = logging.getLogger(__name__)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def create_scope(self) -> Scope:
        return Scope(self)

    def close(self) -> None:
        self._exit_stack.close()
        self._cache.clear()

    def get(self, type_: type[_T]) -> _T:
        if issubclass(type_, Container):
            return cast("_T", self)

        binding = self._registry.lookup(type_)

        try:
            return binding.resolve(self)
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
        return self._get_cached_instance(binding)

    def _get_cached_instance(self, binding: Binding[_T]) -> _T:
        if binding.type_ not in self._cache:
            self._cache[binding.type_] = self._get_instance(binding)
        return cast("_T", self._cache[binding.type_])

    def _get_instance(self, binding: Binding[_T]) -> _T:
        dependencies = {
            name: self.get(dependency.annotation)
            for name, dependency in binding.dependencies.items()
        }
        instance = binding.provider(**dependencies)
        if isinstance(instance, AbstractContextManager) and binding.enter:
            instance = self._exit_stack.enter_context(instance)
        # TODO: if enter is False but instance is a context manager and NOT an instance
        # of registration type, we must enter anyway. Maybe we should handle this at typing
        # level instead
        with suppress(TypeError):
            if not isinstance(instance, binding.type_):
                warnings.warn(
                    f"Container resolved {binding.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        return instance


class Scope(Container):
    def __init__(self, parent: Container) -> None:
        super().__init__(parent._registry)  # noqa: SLF001
        self._parent = parent
        self._logger = logging.getLogger(f"{__name__}.scope")

    def _resolve_singleton(self, binding: Binding[_T]) -> _T:
        return self._parent._resolve_singleton(binding)  # noqa: SLF001
