import asyncio
from typing import TypedDict, cast
from unittest.mock import AsyncMock, Mock, call

import pytest

from handless import Container, Contextual, ResolutionContext, Singleton, Transient
from handless.lifetimes import Lifetime
from tests.helpers import AsyncFakeService, FakeService, FakeServiceWithParams

pytestmark = pytest.mark.anyio
# NOTE: Because Container can resolve asynchronously both sync and async method we always test boths
use_sync_and_async_mock = pytest.mark.parametrize("create_factory", [Mock, AsyncMock])


class FactoryRegistrationOptions(TypedDict, total=False):
    enter: bool
    lifetime: Lifetime


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_and_returns_its_result(
    acontainer: Container,
    acontext: ResolutionContext,
    create_factory: type[Mock | AsyncMock],
) -> None:
    expected = FakeService()
    factory = create_factory(return_value=expected)
    acontainer.register(FakeService).factory(factory)

    resolved = await acontext.aresolve(FakeService)

    assert resolved is expected
    factory.assert_called_once()


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_with_ctx_and_returns_its_result(
    acontainer: Container,
    acontext: ResolutionContext,
    create_factory: type[Mock | AsyncMock],
) -> None:
    expected = FakeService()
    factory = create_factory(wraps=lambda ctx: expected)  # noqa: ARG005
    acontainer.register(FakeService).factory(factory)

    resolved = await acontext.aresolve(FakeService)

    assert resolved is expected
    factory.assert_called_once_with(ctx=acontext)


@use_sync_and_async_mock
async def test_resolve_type_calls_registration_factory_with_dependencies_and_returns_its_result(
    acontainer: Container,
    acontext: ResolutionContext,
    create_factory: type[Mock | AsyncMock],
) -> None:
    factory = create_factory(wraps=FakeServiceWithParams)
    acontainer.register(FakeServiceWithParams).factory(factory)
    acontainer.register(str).factory(AsyncMock(return_value="foo"))
    acontainer.register(int).value(42)

    resolved = await acontext.aresolve(FakeServiceWithParams)

    assert isinstance(resolved, FakeServiceWithParams)
    factory.assert_called_once_with(foo="foo", bar=42)


@pytest.mark.parametrize(
    "options", [FactoryRegistrationOptions(), FactoryRegistrationOptions(enter=True)]
)
async def test_resolve_type_enters_context_manager_returned_by_registration_factory(
    acontainer: Container,
    acontext: ResolutionContext,
    options: FactoryRegistrationOptions,
) -> None:
    acontainer.register(AsyncFakeService).self(**options)

    resolved = await acontext.aresolve(AsyncFakeService)

    assert resolved.entered
    assert not resolved.exited


async def test_resolve_type_not_enter_context_manager_returned_by_registration_factory_when_enter_is_false(
    acontainer: Container, acontext: ResolutionContext
) -> None:
    acontainer.register(AsyncFakeService).self(enter=False)

    resolved = await acontext.aresolve(AsyncFakeService)

    assert not resolved.entered


async def test_resolve_type_not_enter_non_context_manager_object_returned_by_registration_factory(
    container: Container, context: ResolutionContext
) -> None:
    container.register(object).self(enter=True)

    try:
        await context.aresolve(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


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
        acontext: ResolutionContext,
        factory: Mock,
    ) -> AsyncFakeService:
        acontainer.register(AsyncFakeService).factory(factory, **request.param)

        return await acontext.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_on_each_resolve(
        self, resolved: AsyncFakeService, acontext: ResolutionContext, factory: Mock
    ) -> None:
        received = await acontext.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=acontext), call(_=acontext)])

    async def test_calls_and_returns_registration_factory_result_on_different_context(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        acontext: ResolutionContext,
        factory: Mock,
    ) -> None:
        async with acontainer.open_context() as context2:
            received = await context2.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=acontext), call(_=context2)])

    async def test_release_context_exit_entered_context_manager(
        self, acontext: ResolutionContext, resolved: AsyncFakeService
    ) -> None:
        another = await acontext.aresolve(AsyncFakeService)

        await acontext.arelease()

        assert resolved.exited
        assert another.exited


class TestResolveTypeBoundToSingletonRegistration:
    @pytest.fixture(params=[Mock, AsyncMock])
    def factory(self, request: pytest.FixtureRequest) -> Mock:
        AnyMock = cast("type[Mock | AsyncMock]", request.param)  # noqa: N806
        return AnyMock(wraps=lambda _: AsyncFakeService())

    @pytest.fixture
    async def resolved(
        self, acontainer: Container, acontext: ResolutionContext, factory: Mock
    ) -> AsyncFakeService:
        acontainer.register(AsyncFakeService).factory(factory, lifetime=Singleton())

        return await acontext.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_once_per_context(
        self, resolved: AsyncFakeService, acontext: ResolutionContext, factory: Mock
    ) -> None:
        received = await acontext.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=acontext)

    async def test_calls_and_returns_registration_factory_result_once_per_container(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        acontext: Container,
        factory: Mock,
    ) -> None:
        async with acontainer.open_context() as context2:
            received = await context2.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=acontext)

    async def test_resolve_singleton_is_threadsafe(self, acontainer: Container) -> None:
        async def _factory(ctx: ResolutionContext) -> FakeServiceWithParams:
            # Small sleep to force tasks context switch
            await asyncio.sleep(0.01)
            return FakeServiceWithParams(ctx.resolve(str), ctx.resolve(int))

        mock = AsyncMock(wraps=_factory)
        acontainer.register(str).value("foo")
        acontainer.register(int).value(42)
        acontainer.register(FakeServiceWithParams).factory(mock, lifetime=Singleton())

        results = await asyncio.gather(
            *[
                acontainer.open_context().aresolve(FakeServiceWithParams)
                for _ in range(10)
            ]
        )

        mock.assert_called_once()
        assert len(set(results)) == 1

    async def test_release_context_not_exit_entered_context_manager(
        self, acontext: ResolutionContext, resolved: AsyncFakeService
    ) -> None:
        await acontext.arelease()

        assert not resolved.exited

    async def test_release_container_exit_entered_context_manager(
        self, acontainer: Container, resolved: AsyncFakeService
    ) -> None:
        await acontainer.arelease()

        assert resolved.exited

    async def test_release_container_clear_cached_value(
        self,
        acontainer: Container,
        acontext: ResolutionContext,
        resolved: AsyncFakeService,
    ) -> None:
        await acontainer.arelease()

        received = await acontext.aresolve(AsyncFakeService)

        assert received is not resolved

    async def test_release_context_not_clear_cached_value(
        self, acontext: ResolutionContext, resolved: AsyncFakeService
    ) -> None:
        await acontext.arelease()

        received = acontext.resolve(AsyncFakeService)

        assert received is resolved


class TestResolveTypeBoundToContextRegistration:
    @pytest.fixture(params=[Mock, AsyncMock])
    def factory(self, request: pytest.FixtureRequest) -> Mock:
        AnyMock = cast("type[Mock | AsyncMock]", request.param)  # noqa: N806
        return AnyMock(wraps=lambda _: AsyncFakeService())

    @pytest.fixture(autouse=True)
    async def resolved(
        self, acontainer: Container, acontext: ResolutionContext, factory: Mock
    ) -> AsyncFakeService:
        acontainer.register(AsyncFakeService).factory(factory, lifetime=Contextual())

        return await acontext.aresolve(AsyncFakeService)

    async def test_calls_and_returns_registration_factory_result_once_per_context(
        self, resolved: AsyncFakeService, acontext: ResolutionContext, factory: Mock
    ) -> None:
        received = await acontext.aresolve(AsyncFakeService)

        assert received is resolved
        factory.assert_called_once_with(_=acontext)

    async def test_calls_and_returns_registration_factory_result_on_different_context(
        self,
        resolved: AsyncFakeService,
        acontainer: Container,
        acontext: ResolutionContext,
        factory: Mock,
    ) -> None:
        async with acontainer.open_context() as context2:
            received = await context2.aresolve(AsyncFakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=acontext), call(_=context2)])

    async def test_release_context_exit_entered_context_manager(
        self, acontext: ResolutionContext, resolved: AsyncFakeService
    ) -> None:
        await acontext.arelease()

        assert resolved.exited

    async def test_release_context_clear_cached_value(
        self, acontext: ResolutionContext, resolved: AsyncFakeService
    ) -> None:
        await acontext.arelease()

        received = await acontext.aresolve(AsyncFakeService)

        assert received is not resolved
