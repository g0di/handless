import itertools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from unittest.mock import Mock, call

import pytest

from handless import Container, Contextual, ResolutionContext, Singleton, Transient
from handless.lifetimes import Lifetime
from tests.helpers import FakeService, FakeServiceWithParams


class FactoryRegistrationOptions(TypedDict, total=False):
    enter: bool
    lifetime: Lifetime


def test_resolve_type_calls_registration_factory_and_returns_its_result(
    container: Container, context: ResolutionContext
) -> None:
    expected = FakeService()
    factory = Mock(wraps=lambda: expected)
    container.register(FakeService).factory(factory)

    resolved = context.resolve(FakeService)

    assert resolved is expected
    factory.assert_called_once()


def test_resolve_type_calls_registration_factory_with_ctx_and_returns_its_result(
    container: Container, context: ResolutionContext
) -> None:
    expected = FakeService()
    factory = Mock(wraps=lambda ctx: expected)  # noqa: ARG005
    container.register(FakeService).factory(factory)

    resolved = context.resolve(FakeService)

    assert resolved is expected
    factory.assert_called_once_with(ctx=context)


def test_resolve_type_calls_registration_factory_with_dependencies_and_returns_its_result(
    container: Container, context: ResolutionContext
) -> None:
    factory = Mock(wraps=FakeServiceWithParams)
    container.register(FakeServiceWithParams).factory(factory)
    container.register(str).value("foo")
    container.register(int).value(42)

    resolved = context.resolve(FakeServiceWithParams)

    assert isinstance(resolved, FakeServiceWithParams)
    factory.assert_called_once_with(foo="foo", bar=42)


@pytest.mark.parametrize(
    "options", [FactoryRegistrationOptions(), FactoryRegistrationOptions(enter=True)]
)
def test_resolve_type_enters_context_manager_returned_by_registration_factory(
    container: Container,
    context: ResolutionContext,
    options: FactoryRegistrationOptions,
) -> None:
    container.register(FakeService).self(**options)

    resolved = context.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_type_not_enter_context_manager_returned_by_registration_factory_when_enter_is_false(
    container: Container, context: ResolutionContext
) -> None:
    container.register(FakeService).self(enter=False)

    resolved = context.resolve(FakeService)

    assert not resolved.entered


def test_resolve_type_not_enter_non_context_manager_object_returned_by_registration_factory(
    container: Container, context: ResolutionContext
) -> None:
    container.register(object).self(enter=True)

    try:
        context.resolve(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


class TestResolveTypeUsingTransientLifetime:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(
        autouse=True,
        params=[
            FactoryRegistrationOptions(),
            FactoryRegistrationOptions(lifetime=Transient()),
        ],
    )
    def resolved(
        self,
        request: pytest.FixtureRequest,
        container: Container,
        context: ResolutionContext,
        factory: Mock,
    ) -> FakeService:
        container.register(FakeService).factory(factory, **request.param)

        return context.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_on_each_resolve(
        self, resolved: FakeService, context: ResolutionContext, factory: Mock
    ) -> None:
        received = context.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=context), call(_=context)])

    def test_calls_and_returns_registration_factory_result_on_different_context(
        self,
        resolved: FakeService,
        container: Container,
        context: ResolutionContext,
        factory: Mock,
    ) -> None:
        with container.open_context() as context2:
            received = context2.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=context), call(_=context2)])

    def test_release_context_exit_entered_context_manager(
        self, context: ResolutionContext, resolved: FakeService
    ) -> None:
        another = context.resolve(FakeService)

        context.release()

        assert resolved.exited
        assert another.exited


class TestResolveTypeBoundToSingletonRegistration:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture
    def resolved(
        self, container: Container, context: ResolutionContext, factory: Mock
    ) -> FakeService:
        container.register(FakeService).factory(factory, lifetime=Singleton())

        return context.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_once_per_context(
        self, resolved: FakeService, context: ResolutionContext, factory: Mock
    ) -> None:
        received = context.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=context)

    def test_calls_and_returns_registration_factory_result_once_per_container(
        self,
        resolved: FakeService,
        container: Container,
        context: Container,
        factory: Mock,
    ) -> None:
        with ResolutionContext(container) as context2:
            received = context2.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=context)

    def test_resolve_singleton_is_threadsafe(self, container: Container) -> None:
        def _factory(ctx: ResolutionContext) -> FakeServiceWithParams:
            # Small sleep to force threads context switch
            time.sleep(0.01)
            return FakeServiceWithParams(ctx.resolve(str), ctx.resolve(int))

        mock = Mock(wraps=_factory)
        container.register(str).value("foo")
        container.register(int).value(42)
        container.register(FakeService).factory(mock, lifetime=Singleton())

        with ThreadPoolExecutor(100) as pool:
            results = pool.map(
                lambda _: container.open_context().resolve(FakeService), range(100)
            )

        mock.assert_called_once()
        assert len(set(results)) == 1

    def test_release_context_not_exit_entered_context_manager(
        self, context: ResolutionContext, resolved: FakeService
    ) -> None:
        context.release()

        assert not resolved.exited

    def test_release_container_exit_entered_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.release()

        assert resolved.exited

    def test_release_container_clear_cached_value(
        self, container: Container, context: ResolutionContext, resolved: FakeService
    ) -> None:
        container.release()

        received = context.resolve(FakeService)

        assert received is not resolved

    def test_release_context_not_clear_cached_value(
        self, context: ResolutionContext, resolved: FakeService
    ) -> None:
        context.release()

        received = context.resolve(FakeService)

        assert received is resolved


class TestResolveTypeBoundToContextdRegistration:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, container: Container, context: ResolutionContext, factory: Mock
    ) -> FakeService:
        container.register(FakeService).factory(factory, lifetime=Contextual())

        return context.resolve(FakeService)

    def test_calls_and_returns_registration_factory_result_once_per_context(
        self, resolved: FakeService, context: ResolutionContext, factory: Mock
    ) -> None:
        received = context.resolve(FakeService)

        assert received is resolved
        factory.assert_called_once_with(_=context)

    def test_calls_and_returns_registration_factory_result_on_different_context(
        self,
        resolved: FakeService,
        container: Container,
        context: ResolutionContext,
        factory: Mock,
    ) -> None:
        with ResolutionContext(container) as context2:
            received = context2.resolve(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(_=context), call(_=context2)])

    def test_release_context_exit_entered_context_manager(
        self, context: ResolutionContext, resolved: FakeService
    ) -> None:
        context.release()

        assert resolved.exited

    def test_release_context_clear_cached_value(
        self, context: ResolutionContext, resolved: FakeService
    ) -> None:
        context.release()

        received = context.resolve(FakeService)

        assert received is not resolved


class TestOverrideTypes:
    @pytest.fixture
    def factory(self, container: Container) -> Mock:
        factory = Mock(wraps=FakeService)
        container.register(FakeService).factory(factory)
        return factory

    @pytest.fixture
    def factory_override(self, container: Container) -> Mock:
        factory_override = Mock(wraps=FakeService)
        container.override(FakeService).factory(factory_override)
        return factory_override

    def test_resolve_type_calls_override_factory_and_returns_its_result_when_registered(
        self, context: ResolutionContext, factory: Mock, factory_override: Mock
    ) -> None:
        resolved = context.resolve(FakeService)

        assert isinstance(resolved, FakeService)
        factory_override.assert_called_once_with()
        factory.assert_not_called()

    def test_release_container_clear_overrides(
        self,
        container: Container,
        context: ResolutionContext,
        factory: Mock,
        factory_override: Mock,
    ) -> None:
        container.release()
        context.resolve(FakeService)

        factory.assert_called_once_with()
        factory_override.assert_not_called()

    def test_override_can_override_an_already_overridden_type(
        self,
        container: Container,
        context: ResolutionContext,
        factory: Mock,
        factory_override: Mock,
    ) -> None:
        factory_override2 = Mock(wraps=FakeService)
        container.override(FakeService).factory(factory_override2)

        context.resolve(FakeService)

        factory.assert_not_called()
        factory_override.assert_not_called()
        factory_override2.assert_called_once_with()

    @pytest.mark.parametrize(
        ("lifetime", "override_lifetime"),
        [
            # Ensure that whatever lifetimes are used, override always takes precedence
            *itertools.permutations([Transient(), Contextual(), Singleton()], 2),
            (Transient(), Transient()),
            (Singleton(), Singleton()),
            (Contextual(), Contextual()),
        ],
    )
    def test_override_a_cached_type_returns_override_result(
        self,
        container: Container,
        context: ResolutionContext,
        lifetime: Lifetime,
        override_lifetime: Lifetime,
    ) -> None:
        factory = Mock(wraps=FakeService)
        factory_override2 = Mock(wraps=FakeService)

        container.register(FakeService).factory(factory, lifetime=lifetime)
        singleton = context.resolve(FakeService)
        container.override(FakeService).factory(
            factory_override2, lifetime=override_lifetime
        )

        override = context.resolve(FakeService)

        assert override is not singleton
