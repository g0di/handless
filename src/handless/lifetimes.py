from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from handless.context import ResolutionContext

if TYPE_CHECKING:
    from handless._bindings import Binding
    from handless.container import Releasable, Scope


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


_resolvers = weakref.WeakKeyDictionary["Releasable[Any]", ResolutionContext]()


def get_context_for(obj: Releasable[Any]) -> ResolutionContext:
    """Get or create a resolution context for given closable."""
    if obj not in _resolvers:
        _resolvers[obj] = resolver = ResolutionContext()
        obj.on_release(resolver.close)
    return _resolvers[obj]
