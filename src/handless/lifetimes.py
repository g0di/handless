from __future__ import annotations

import warnings
import weakref
from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack, suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from handless._registry import Registration
    from handless.container import ResolutionContext


_T = TypeVar("_T")


class Lifetime(Protocol):
    def resolve(self, scope: ResolutionContext, binding: Registration[_T]) -> _T:
        """Resolve given binding within given scope."""


# NOTE: We use dataclasses for lifetime to simplify equality comparisons.


@dataclass(slots=True)
class Transient(Lifetime):
    """Calls binding factory on each resolve."""

    def resolve(self, scope: ResolutionContext, binding: Registration[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_instance(binding, scope)


@dataclass(slots=True)
class Contextual(Lifetime):
    """Calls binding factory on resolve once per context."""

    def resolve(self, scope: ResolutionContext, binding: Registration[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_cached_instance(binding, scope)


@dataclass(slots=True)
class Singleton(Lifetime):
    """Calls binding factory on resolve once per container."""

    def resolve(self, scope: ResolutionContext, binding: Registration[_T]) -> _T:
        ctx = get_context_for(scope.container)
        return ctx.get_cached_instance(binding, scope)


ReleaseCallback = Callable[[], Any]
_resolution_contexts = weakref.WeakKeyDictionary["Releasable[Any]", "LifetimeContext"]()


def get_context_for(obj: Releasable[Any]) -> LifetimeContext:
    """Get or create a lifetime context for given releasable object."""
    if obj not in _resolution_contexts:
        _resolution_contexts[obj] = ctx = LifetimeContext()
        obj.on_release(ctx.close)
    return _resolution_contexts[obj]


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


class LifetimeContext:
    """Holds cached resolved objects and their context managers."""

    def __init__(self) -> None:
        self._cache: dict[type[Any], Any] = {}
        self._exit_stack = ExitStack()

    def close(self) -> None:
        """Exit all entered context managers and clear cached values."""
        self._exit_stack.close()
        self._cache.clear()

    def get_cached_instance(
        self, binding: Registration[_T], ctx: ResolutionContext
    ) -> _T:
        if binding.type_ not in self._cache:
            self._cache[binding.type_] = self.get_instance(binding, ctx)
        return cast("_T", self._cache[binding.type_])

    def get_instance(self, binding: Registration[_T], ctx: ResolutionContext) -> _T:
        args, kwargs = self._resolve_dependencies(binding, ctx)
        instance = binding.factory(*args, **kwargs)

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

    def _resolve_dependencies(
        self, binding: Registration[_T], ctx: ResolutionContext
    ) -> tuple[list[Any], dict[str, Any]]:
        args = []
        kwargs: dict[str, Any] = {}

        for dep in binding.dependencies:
            resolved = ctx.resolve(dep.type_)
            if dep.positional_only:
                args.append(resolved)
                continue
            kwargs[dep.name] = resolved

        return args, kwargs

    def __del__(self) -> None:
        # NOTE: there is no other ways than using exit stack private attr to get
        # the remaining number of callbacks
        if self._exit_stack._exit_callbacks:  # type: ignore [attr-defined] # noqa: SLF001
            warnings.warn(
                "Lifetime context has been garbage-collected without being closed."
                " You may have forgot to call `.release()` on a scope or container",
                ResourceWarning,
                stacklevel=1,
            )
