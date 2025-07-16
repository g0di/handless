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
    container.register(FakeService).factory(factory)
    container.register(str).value("foo")
    container.register(int).value(42)

    resolved = context.resolve(FakeService)

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

    @pytest.fixture(autouse=True)
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

    def test_calls_and_returns_registration_factory_result_once_accross_contexts(
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
