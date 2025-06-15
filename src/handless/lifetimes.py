from __future__ import annotations

import weakref
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from handless.context import ResolutionContext

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.container import Scope


_T = TypeVar("_T")


class Lifetime(Protocol):
    def resolve(self, scope: Scope, binding: Binding[_T]) -> _T:
        """Resolve given binding within given scope."""


# NOTE: we use dataclasses for lifetime to simplify equality comparisons.


@dataclass
class Transient(Lifetime):
    """Calls binding provider on each resolve."""

    def resolve(self, scope: Scope, binding: Binding[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_instance(binding, scope)


@dataclass
class Scoped(Lifetime):
    """Calls binding provider on resolve once per scope."""

    def resolve(self, scope: Scope, binding: Binding[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_cached_instance(binding, scope)


@dataclass
class Singleton(Lifetime):
    """Calls binding provider on resolve once per container."""

    def resolve(self, scope: Scope, binding: Binding[_T]) -> _T:
        ctx = get_context_for(scope.container)
        return ctx.get_cached_instance(binding, scope)


ReleaseCallback = Callable[[], Any]


class Releasable(AbstractContextManager[_T]):
    """Supports release method and registering callbacks on release."""

    def __init__(self) -> None:
        self._on_release_callbacks: list[ReleaseCallback] = []

    def __exit__(self, *args: object) -> None:
        self.release()

    def on_release(self, callback: ReleaseCallback) -> None:
        self._on_release_callbacks.append(callback)

    def release(self) -> None:
        """Release cached instances and exit entered context managers.

        Note that the object is still fully usable afterwards.
        """
        for cb in self._on_release_callbacks:
            cb()


_resolution_contexts = weakref.WeakKeyDictionary["Releasable[Any]", ResolutionContext]()


def get_context_for(obj: Releasable[Any]) -> ResolutionContext:
    """Get or create a resolution context for given closable."""
    if obj not in _resolution_contexts:
        _resolution_contexts[obj] = ctx = ResolutionContext()
        obj.on_release(ctx.close)
    return _resolution_contexts[obj]
