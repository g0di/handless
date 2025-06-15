from __future__ import annotations

import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.container import Scope

_T = TypeVar("_T")


class ResolutionContext:
    """Holds cached bindings resolved objects and their context managers."""

    def __init__(self) -> None:
        self._cache: dict[type[Any], Any] = {}
        self._exit_stack = ExitStack()

    def close(self) -> None:
        self._exit_stack.close()
        self._cache.clear()

    def get_cached_instance(self, binding: Binding[_T], scope: Scope) -> _T:
        if binding.type_ not in self._cache:
            self._cache[binding.type_] = self.get_instance(binding, scope)
        return cast("_T", self._cache[binding.type_])

    def get_instance(self, binding: Binding[_T], scope: Scope) -> _T:
        instance = binding.provider(scope)
        if isinstance(instance, AbstractContextManager) and binding.enter:
            instance = self._exit_stack.enter_context(instance)

        with suppress(TypeError):
            if not isinstance(instance, binding.type_):
                warnings.warn(
                    f"Container resolved {binding.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    RuntimeWarning,
                    stacklevel=2,
                )
        # NOTE: Normally type annotations should prevent having enter=False with instance
        # not being an instance of resolved type. Still, at this point in code there
        # is not way to enforce this so we just return the value anyway
        return cast("_T", instance)
