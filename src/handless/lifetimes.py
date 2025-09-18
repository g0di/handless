from __future__ import annotations

import asyncio
import logging
import warnings
import weakref
from collections import defaultdict, deque
from contextlib import AbstractAsyncContextManager, AbstractContextManager, suppress
from threading import Lock, RLock
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from types import TracebackType

    from handless._container import ResolutionContext
    from handless._registry import Registration


_T = TypeVar("_T")


class Lifetime(Protocol):
    def resolve(self, context: ResolutionContext, registration: Registration[_T]) -> _T:
        """Resolve given registration within given context."""

    async def aresolve(
        self, context: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        """Asynchrnously resolve given registration within given context."""


class Transient(Lifetime):
    """Calls registration factory on each resolve."""

    def resolve(self, context: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = LifetimeContext.get(context)
        return ctx.get_instance(context, registration)

    async def aresolve(
        self, context: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        ctx = LifetimeContext.get(context)
        return await ctx.aget_instance(context, registration)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Transient)


class Contextual(Lifetime):
    """Calls registration factory on resolve once per context."""

    def resolve(self, context: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = LifetimeContext.get(context)
        return ctx.get_cached_instance(context, registration)

    async def aresolve(
        self, context: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        ctx = LifetimeContext.get(context)
        return await ctx.aget_cached_instance(context, registration)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Contextual)


class Singleton(Lifetime):
    """Calls registration factory on resolve once per container."""

    def resolve(self, context: ResolutionContext, registration: Registration[_T]) -> _T:
        ctx = LifetimeContext.get(context.container)
        return ctx.get_cached_instance(context, registration)

    async def aresolve(
        self, context: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        ctx = LifetimeContext.get(context.container)
        return await ctx.aget_cached_instance(context, registration)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Singleton)


class Releasable(AbstractContextManager[_T], AbstractAsyncContextManager[_T]):
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        LifetimeContext.get(self).__exit__(exc_type, exc_val, exc_tb)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await LifetimeContext.get(self).__aexit__(exc_type, exc_val, exc_tb)

    def release(self) -> None:
        """Release cached instances and exit entered context managers.

        Note that the object is still fully usable afterwards.
        """
        self.__exit__(None, None, None)

    async def arelease(self) -> None:
        """Release cached instances and exit entered context managers.

        Note that the object is still fully usable afterwards.
        """
        await self.__aexit__(None, None, None)


class LifetimeContext(Releasable["LifetimeContext"]):
    """Holds cached resolved objects and their context managers."""

    _contexts = weakref.WeakKeyDictionary[object, "LifetimeContext"]()

    @classmethod
    def get(cls, obj: object) -> LifetimeContext:
        """Get or create a lifetime context for given releasable."""
        if obj not in cls._contexts:
            cls._contexts[obj] = cls()
        return cls._contexts[obj]

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._cache: dict[int, Any] = {}
        self._lock = Lock()
        self._async_lock = asyncio.Lock()
        self._registration_locks = defaultdict[int, RLock](RLock)
        self._async_registration_locks = defaultdict[int, asyncio.Lock](asyncio.Lock)
        self._entered_context_managers = deque[
            AbstractContextManager[Any] | AbstractAsyncContextManager[Any]
        ]()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        while self._entered_context_managers:
            cm = self._entered_context_managers.pop()
            if isinstance(cm, AbstractAsyncContextManager):
                warnings.warn(
                    f"SKipped exiting async context manager {cm} in sync cleanup, use `arelease()` or `async with`.",
                    UserWarning,
                    stacklevel=1,
                )
                continue

            try:
                cm.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                # TODO: reraise the last exception (just like an exit stack)
                self._logger.exception("Failed exiting context manager {cm}.")

        self._cache.clear()
        self._registration_locks.clear()
        self._async_registration_locks.clear()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        while self._entered_context_managers:
            cm = self._entered_context_managers.pop()

            try:
                if isinstance(cm, AbstractAsyncContextManager):
                    await cm.__aexit__(exc_type, exc_val, exc_tb)
                else:
                    cm.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                # TODO: reraise the last exception (just like an exit stack)
                self._logger.exception("Failed exiting context manager {cm}.")

        self._cache.clear()
        self._registration_locks.clear()
        self._async_registration_locks.clear()

    def release(self) -> None:
        self.__exit__(None, None, None)

    async def arelease(self) -> None:
        await self.__aexit__(None, None, None)

    def get_cached_instance(
        self, ctx: ResolutionContext, registration: Registration[_T]
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
                self._cache[registration_hash] = self.get_instance(ctx, registration)
            return cast("_T", self._cache[registration_hash])

    async def aget_cached_instance(
        self, ctx: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        # NOTE: use registration object ID allowing to not get previously cached value
        # for a type already resolved but overriden afterwards (Override will register
        # another registration object).
        registration_hash = id(registration)

        async with self._async_lock:
            # Use a context shared lock to ensure all threads use the same lock
            # per registration
            registration_lock = self._async_registration_locks[registration_hash]

        async with registration_lock:
            # Use a context and registration shared lock to ensure a single thread
            # can run the following code. This will ensure we can not end up with
            # two instances of a singleton lifetime registration if two threads
            # resolve it at the same time
            if registration_hash not in self._cache:
                self._cache[registration_hash] = await self.aget_instance(
                    ctx, registration
                )
            return cast("_T", self._cache[registration_hash])

    def get_instance(
        self, ctx: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        args, kwargs = self._resolve_dependencies(registration, ctx)
        instance = registration.factory(*args, **kwargs)

        if asyncio.iscoroutine(instance):
            instance.close()
            msg = f"Cannot resolve coroutine {instance}. Use `aresolve()` instead."
            raise TypeError(msg)
        if isinstance(instance, AbstractAsyncContextManager):
            msg = f"Cannot resolve async context manager {instance}. Use `aresolve()` instead."
            raise TypeError(msg)
        if isinstance(instance, AbstractContextManager) and registration.enter:
            self._entered_context_managers.append(instance)
            instance = instance.__enter__()

        with suppress(TypeError):
            if not isinstance(instance, registration.type_):
                warnings.warn(
                    f"Container resolved {registration.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    UserWarning,
                    stacklevel=4,
                )
        # NOTE: Normally type annotations should prevent having enter=False with instance
        # not being an instance of resolved type. Still, at this point in code there
        # is not way to enforce this so we just return the value anyway
        return cast("_T", instance)

    async def aget_instance(
        self, ctx: ResolutionContext, registration: Registration[_T]
    ) -> _T:
        args, kwargs = await self._aresolve_dependencies(registration, ctx)
        instance = registration.factory(*args, **kwargs)

        if asyncio.iscoroutine(instance):
            instance = await instance
        if isinstance(instance, AbstractAsyncContextManager) and registration.enter:
            self._entered_context_managers.append(instance)
            instance = await instance.__aenter__()
        if isinstance(instance, AbstractContextManager) and registration.enter:
            self._entered_context_managers.append(instance)
            instance = instance.__enter__()

        with suppress(TypeError):
            if not isinstance(instance, registration.type_):
                warnings.warn(
                    f"Container resolved {registration.type_} with {instance} which is not an instance of this type. "
                    "This could lead to unexpected errors.",
                    UserWarning,
                    stacklevel=4,
                )
        # NOTE: Normally type annotations should prevent having enter=False with instance
        # not being an instance of resolved type. Still, at this point in code there
        # is no way to enforce this so we just return the value anyway
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

    async def _aresolve_dependencies(
        self, registration: Registration[_T], ctx: ResolutionContext
    ) -> tuple[list[Any], dict[str, Any]]:
        args = []
        kwargs: dict[str, Any] = {}

        for dep in registration.dependencies:
            resolved = await ctx.aresolve(dep.type_)
            if dep.positional_only:
                args.append(resolved)
                continue
            kwargs[dep.name] = resolved

        return args, kwargs

    def __del__(self) -> None:
        if self._entered_context_managers:
            warnings.warn(
                "A Container or ResolutionContext has been garbage-collected with pending resources."
                " Did you forget to call `release()` or `arelease()`?",
                UserWarning,
                stacklevel=1,
            )
