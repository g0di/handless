import asyncio
from typing import TypedDict, cast
from unittest.mock import AsyncMock, Mock, call

import pytest

from handless import Container, Scope, Scoped, Singleton, Transient
from handless.lifetimes import Lifetime
from tests.helpers import AsyncFakeService, FakeService, FakeServiceWithParams

pytestmark = pytest.mark.anyio
# NOTE: Because Container can resolve asynchronously both sync and async method we always test boths
use_sync_and_async_mock = pytest.mark.parametrize("create_factory", [Mock, AsyncMock])


class FactoryRegistrationOptions(TypedDict, total=False):
    managed: bool
    lifetime: Lifetime


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_and_returns_its_result(
    acontainer: Container, ascope: Scope, create_factory: type[Mock | AsyncMock]
) -> None:
    expected = FakeService()
    factory = create_factory(return_value=expected)
    acontainer.bind(FakeService).to_factory(factory)

    resolved = await ascope.aresolve(FakeService)

    assert resolved is expected
    factory.assert_called_once()


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_with_ctx_and_returns_its_result(
    acontainer: Container, ascope: Scope, create_factory: type[Mock | AsyncMock]
) -> None:
    expected = FakeService()
    factory = create_factory(wraps=lambda ctx: expected)  # noqa: ARG005
    acontainer.bind(FakeService).to_factory(factory)

    resolved = await ascope.aresolve(FakeService)

    assert resolved is expected
    factory.assert_called_once_with(ctx=ascope)


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_with_dependencies_and_returns_its_result(
    acontainer: Container, ascope: Scope, create_factory: type[Mock | AsyncMock]
) -> None:
    factory = create_factory(wraps=FakeServiceWithParams)
    acontainer.bind(FakeServiceWithParams).to_factory(factory)
    acontainer.bind(str).to_factory(AsyncMock(return_value="foo"))
    acontainer.bind(int).to_value(42)

    resolved = await ascope.aresolve(FakeServiceWithParams)

    assert isinstance(resolved, FakeServiceWithParams)
    factory.assert_called_once_with(foo="foo", bar=42)


@pytest.mark.parametrize(
    "options", [FactoryRegistrationOptions(), FactoryRegistrationOptions(managed=True)]
)
async def test_resolve_type_enters_context_manager_returned_by_registration_factory(
    acontainer: Container, ascope: Scope, options: FactoryRegistrationOptions
) -> None:
    acontainer.bind(AsyncFakeService).to_self(**options)

    resolved = await ascope.aresolve(AsyncFakeService)

    assert resolved.entered
    assert not resolved.exited


async def test_resolve_type_not_enter_context_manager_returned_by_registration_factory_when_managed_is_false(
    acontainer: Container, ascope: Scope
) -> None:
    acontainer.bind(AsyncFakeService).to_self(managed=False)

    resolved = await ascope.aresolve(AsyncFakeService)

    assert not resolved.entered


async def test_resolve_type_not_enter_non_context_manager_object_returned_by_registration_factory(
    container: Container, scope: Scope
) -> None:
    container.bind(object).to_self(managed=True)

    try:
        await scope.aresolve(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


class TestContainerAresolveShortcut:
    async def test_resolves_type_without_manual_scope(
        self, acontainer: Container
    ) -> None:
        expected = object()
        acontainer.bind(object).to_value(expected)

        async with acontainer.aresolve(object) as resolved:
            assert resolved is expected

    async def test_uses_new_scope_for_each_call(self, acontainer: Container) -> None:
        acontainer.bind(AsyncFakeService).to_self(Scoped())

        async with acontainer.aresolve(AsyncFakeService) as first:
            pass

        async with acontainer.aresolve(AsyncFakeService) as second:
            pass

        assert first is not second

    async def test_releases_temporary_scope(self, acontainer: Container) -> None:
        acontainer.bind(AsyncFakeService).to_self(Scoped())

        async with acontainer.aresolve(AsyncFakeService) as resolved:
            assert resolved.entered
            assert not resolved.exited

        assert resolved.exited

    async def test_resolves_several_types_in_single_call(
        self, acontainer: Container
    ) -> None:
        expected_number = 42
        acontainer.bind(str).to_value("foo")
        acontainer.bind(int).to_value(expected_number)

        async with acontainer.aresolve(str, int) as (text, number):
            assert text == "foo"
            assert number == expected_number

    async def test_aresolve_several_types_keeps_temporary_scope_alive(
        self, acontainer: Container
    ) -> None:
        expected_number = 42
        acontainer.bind(AsyncFakeService).to_self(Scoped())
        acontainer.bind(int).to_value(expected_number)

        async with acontainer.aresolve(AsyncFakeService, int) as (service, number):
            assert number == expected_number
            assert service.entered
            assert not service.exited

        assert service.exited


class TestResolveTypeUsingTransientLifetime:
    @pytest.fixture(params=[Mock, AsyncMock])
    def factory(self, request: pytest.FixtureRequest) -> Mock:
        AnyMock = cast("type[Mock | AsyncMock]", request.param)  # noqa: N806
        return AnyMock(wraps=lambda _: AsyncFakeService())

    @pytest.fixture(
        autouse=True,
        params=[
            FactoryRegistrationOptions(),
            FactoryRegistrationOptions(lifetime=Transient()),
        ],
    )
    async def resolved(
        self,
        request: pytest.FixtureRequest,
        acontainer: Container,
        ascope: Scope,
        factory: Mock,
    ) -> AsyncFakeService:
        acontainer.bind(AsyncFakeService).to_factory(factory, **request.param)

        return await ascope.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_on_each_resolve(
        self, resolved: AsyncFakeService, ascope: Scope, factory: Mock
    ) -> None:
        received = await ascope.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=ascope), call(_=ascope)])

    async def test_calls_and_returns_registration_factory_result_on_different_scope(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        ascope: Scope,
        factory: Mock,
    ) -> None:
        async with acontainer.create_scope() as scope2:
            received = await scope2.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=ascope), call(_=scope2)])

    async def test_release_scope_exit_entered_context_manager(
        self, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        another = await ascope.aresolve(AsyncFakeService)

        await ascope.aclose()

        assert resolved.exited
        assert another.exited


class TestResolveTypeBoundToSingletonRegistration:
    @pytest.fixture(params=[Mock, AsyncMock])
    def factory(self, request: pytest.FixtureRequest) -> Mock:
        AnyMock = cast("type[Mock | AsyncMock]", request.param)  # noqa: N806
        return AnyMock(wraps=lambda _: AsyncFakeService())

    @pytest.fixture
    async def resolved(
        self, acontainer: Container, ascope: Scope, factory: Mock
    ) -> AsyncFakeService:
        acontainer.bind(AsyncFakeService).to_factory(factory, Singleton())

        return await ascope.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_once_per_scope(
        self, resolved: AsyncFakeService, ascope: Scope, factory: Mock
    ) -> None:
        received = await ascope.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=ascope)

    async def test_calls_and_returns_registration_factory_result_once_per_container(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        ascope: Scope,
        factory: Mock,
    ) -> None:
        async with acontainer.create_scope() as scope2:
            received = await scope2.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=ascope)

    async def test_resolve_singleton_is_threadsafe(self, acontainer: Container) -> None:
        async def _factory(ctx: Scope) -> FakeServiceWithParams:
            # Small sleep to force tasks context switch
            await asyncio.sleep(0.01)
            return FakeServiceWithParams(ctx.resolve(str), ctx.resolve(int))

        mock = AsyncMock(wraps=_factory)
        acontainer.bind(str).to_value("foo")
        acontainer.bind(int).to_value(42)
        acontainer.bind(FakeServiceWithParams).to_factory(mock, Singleton())

        results = await asyncio.gather(
            *[
                acontainer.create_scope().aresolve(FakeServiceWithParams)
                for _ in range(10)
            ]
        )

        mock.assert_called_once()
        assert len(set(results)) == 1

    async def test_release_scope_not_exit_entered_context_manager(
        self, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        await ascope.aclose()

        assert not resolved.exited

    async def test_release_container_exit_entered_context_manager(
        self, acontainer: Container, resolved: AsyncFakeService
    ) -> None:
        await acontainer.aclose()

        assert resolved.exited

    async def test_release_container_clear_cached_value(
        self, acontainer: Container, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        await acontainer.aclose()

        received = await ascope.aresolve(AsyncFakeService)

        assert received is not resolved

    async def test_release_scope_not_clear_cached_value(
        self, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        await ascope.aclose()

        received = ascope.resolve(AsyncFakeService)

        assert received is resolved


class TestResolveTypeBoundToScopeRegistration:
    @pytest.fixture(params=[Mock, AsyncMock])
    def factory(self, request: pytest.FixtureRequest) -> Mock:
        AnyMock = cast("type[Mock | AsyncMock]", request.param)  # noqa: N806
        return AnyMock(wraps=lambda _: AsyncFakeService())

    @pytest.fixture(autouse=True)
    async def resolved(
        self, acontainer: Container, ascope: Scope, factory: Mock
    ) -> AsyncFakeService:
        acontainer.bind(AsyncFakeService).to_factory(factory, Scoped())

        return await ascope.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_once_per_scope(
        self, resolved: AsyncFakeService, ascope: Scope, factory: Mock
    ) -> None:
        received = await ascope.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=ascope)

    async def test_calls_and_returns_registration_factory_result_on_different_scope(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        ascope: Scope,
        factory: Mock,
    ) -> None:
        async with acontainer.create_scope() as scope2:
            received = await scope2.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=ascope), call(_=scope2)])

    async def test_release_scope_exit_entered_context_manager(
        self, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        await ascope.aclose()

        assert resolved.exited

    async def test_release_scope_clear_cached_value(
        self, ascope: Scope, resolved: AsyncFakeService
    ) -> None:
        await ascope.aclose()

        received = await ascope.aresolve(AsyncFakeService)

        assert received is not resolved


class TestContainerCloseWithScopes:
    async def test_container_close_closes_referenced_scopes(
        self, acontainer: Container
    ) -> None:
        """Verify that container.aclose() closes all referenced scopes."""
        acontainer.bind(AsyncFakeService).to_self(lifetime=Singleton())
        scope = acontainer.create_scope()
        service = await scope.aresolve(AsyncFakeService)

        assert service.entered
        assert not service.exited

        await acontainer.aclose()

        assert service.exited

    async def test_container_close_no_error_when_unreferenced_scopes_garbage_collected(
        self, acontainer: Container
    ) -> None:
        """Verify container.aclose() handles scopes that are garbage collected (weakref).

        When a scope is no longer referenced and garbage collected, it should
        automatically disappear from the container's weakref set, and closing
        the container should not raise any errors.
        """
        import gc

        acontainer.bind(AsyncFakeService).to_self(lifetime=Singleton())

        async def create_unreferenced_scope_and_resolve_service() -> AsyncFakeService:
            scope = acontainer.create_scope()
            return await scope.aresolve(AsyncFakeService)

        service = await create_unreferenced_scope_and_resolve_service()
        gc.collect()

        await acontainer.aclose()

        assert service.exited
