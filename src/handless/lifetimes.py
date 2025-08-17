from __future__ import annotations

import warnings
import weakref
from collections import defaultdict
from collections.abc import Callable
from contextlib import AbstractContextManager, ExitStack, suppress
from threading import Lock, RLock
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from handless._registry import Registration
    from handless.container import ResolutionContext


_T = TypeVar("_T")


class Lifetime(Protocol):
    def resolve(self, scope: ResolutionContext, registration: Registration[_T]) -> _T:
        """Resolve given registration within given scope."""


# NOTE: We use dataclasses for lifetime to simplify equality comparisons.


class Transient(Lifetime):
    """Calls registration factory on each resolve."""

    def resolve(self, scope: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_instance(registration, scope)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Transient)


class Contextual(Lifetime):
    """Calls registration factory on resolve once per context."""

    def resolve(self, scope: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = get_context_for(scope)
        return ctx.get_cached_instance(registration, scope)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Contextual)


class Singleton(Lifetime):
    """Calls registration factory on resolve once per container."""

    def resolve(self, scope: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = get_context_for(scope.container)
        return ctx.get_cached_instance(registration, scope)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Singleton)


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
        self._cache: dict[int, Any] = {}
        self._exit_stack = ExitStack()
        self._lock = Lock()
        self._registration_locks = defaultdict[int, RLock](RLock)

    def close(self) -> None:
        """Exit all entered context managers and clear cached values."""
        self._exit_stack.close()
        self._cache.clear()

    def get_cached_instance(
        self, registration: Registration[_T], ctx: ResolutionContext
    ) -> _T:
        # NOTE: use registration object ID allowing to not get previously cached value
        # for a type already resolved but overriden afterwards (Override will register
        # another registration object).
        registration_hash = id(registration)

        with self._lock:
            # Use a context shared lock to ensure all threads use the same lock
            # per registration
            registration_lock = self._registration_locks[registration_hash]

        with registration_lock:
            # Use a context and registration shared lock to ensure a single thread
            # can run the following code. This will ensure we can not end up with
            # two instances of a singleton lifetime registration if two threads
            # resolve it at the same time
            if registration_hash not in self._cache:
                self._cache[registration_hash] = self.get_instance(registration, ctx)
            return cast("_T", self._cache[registration_hash])

    def get_instance(
        self, registration: Registration[_T], ctx: ResolutionContext
    ) -> _T:
        args, kwargs = self._resolve_dependencies(registration, ctx)
        instance = registration.factory(*args, **kwargs)

        if isinstance(instance, AbstractContextManager) and registration.enter:
            instance = self._exit_stack.enter_context(instance)

        with suppress(TypeError):
            if not isinstance(instance, registration.type_):
                warnings.warn(
                    f"Container resolved {registration.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    Warning,
                    stacklevel=4,
                )
        # NOTE: Normally type annotations should prevent having enter=False with instance
        # not being an instance of resolved type. Still, at this point in code there
        # is not way to enforce this so we just return the value anyway
        return cast("_T", instance)

    def _resolve_dependencies(
        self, registration: Registration[_T], ctx: ResolutionContext
    ) -> tuple[list[Any], dict[str, Any]]:
        args = []
        kwargs: dict[str, Any] = {}

        for dep in registration.dependencies:
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
