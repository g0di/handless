from __future__ import annotations

import logging
import warnings
from contextlib import AbstractContextManager, ExitStack, suppress
from typing import TYPE_CHECKING, Any, TypeVar, cast

from handless.exceptions import ResolveError

if TYPE_CHECKING:
    from handless._registrations import Registration
    from handless.registry import Registry


_T = TypeVar("_T")


class Container:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._cache: dict[type[Any], Any] = {}
        self._exit_stack = ExitStack()
        self._logger = logging.getLogger(__name__)

    def create_scope(self) -> Scope:
        return Scope(self)

    def close(self) -> None:
        self._exit_stack.close()
        self._cache.clear()

    def resolve(self, type_: type[_T]) -> _T:
        if issubclass(type_, Container):
            return cast("_T", self)

        registration = self._registry.lookup(type_)

        try:
            return registration.resolve(self)
        except Exception as error:
            raise ResolveError(type_) from error
        finally:
            self._logger.info(
                "Resolved %s%s: %s",
                type_,
                " (unregistered)" if type_ in self._registry else "",
                registration,
            )

    def _resolve_transient(self, registration: Registration[_T]) -> _T:
        return self._get_instance(registration)

    def _resolve_singleton(self, registration: Registration[_T]) -> _T:
        return self._get_cached_instance(registration)

    def _resolve_scoped(self, registration: Registration[_T]) -> _T:  # noqa: ARG002
        msg = "Can not resolve scoped type outside a scope"
        raise ValueError(msg)

    def _get_cached_instance(self, registration: Registration[_T]) -> _T:
        if registration.type_ not in self._cache:
            self._cache[registration.type_] = self._get_instance(registration)
        return cast("_T", self._cache[registration.type_])

    def _get_instance(self, registration: Registration[_T]) -> _T:
        instance = registration.provider(self)
        if isinstance(instance, AbstractContextManager) and registration.enter:
            instance = self._exit_stack.enter_context(instance)
        # TODO: if enter is False but instance is a context manager and NOT an instance
        # of registration type, we must enter anyway. Maybe we should handle this at typing
        # level instead
        with suppress(TypeError):
            if not isinstance(instance, registration.type_):
                warnings.warn(
                    f"Container resolved {registration.type_} with {instance} which is not an instance of this type. "
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

    def _resolve_singleton(self, registration: Registration[_T]) -> _T:
        return self._parent._resolve_singleton(registration)  # noqa: SLF001

    def _resolve_scoped(self, registration: Registration[_T]) -> _T:
        return self._get_cached_instance(registration)
