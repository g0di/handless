from typing import TypedDict
from unittest.mock import Mock, call

import pytest

from handless import Container, Scope, Scoped, Singleton, Transient
from handless.lifetimes import Lifetime
from tests.helpers import FakeService


class ProviderBindingOptions(TypedDict, total=False):
    enter: bool
    lifetime: Lifetime


def test_resolve_type_calls_binding_provider_and_returns_its_result(
    container: Container, scope: Scope
) -> None:
    expected = FakeService()
    provider = Mock(wraps=lambda: expected)
    container.register(FakeService).factory(provider)

    resolved = scope.resolve(FakeService)

    assert resolved is expected
    provider.assert_called_once()


@pytest.mark.parametrize(
    "options", [ProviderBindingOptions(), ProviderBindingOptions(enter=True)]
)
def test_resolve_type_enters_context_manager_returned_by_binding_provider(
    container: Container, scope: Scope, options: ProviderBindingOptions
) -> None:
    container.register(FakeService).factory(lambda _: FakeService(), **options)

    resolved = scope.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_type_not_enter_context_manager_returned_by_binding_provider_when_enter_is_false(
    container: Container, scope: Scope
) -> None:
    container.register(FakeService).factory(lambda _: FakeService(), enter=False)

    resolved = scope.resolve(FakeService)

    assert not resolved.entered


def test_resolve_type_not_enter_non_context_manager_object_returned_by_binding_provider(
    container: Container, scope: Scope
) -> None:
    container.register(object).factory(lambda _: object(), enter=True)

    try:
        scope.resolve(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


class TestResolveTypeBoundToTransientBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(
        autouse=True,
        params=[ProviderBindingOptions(), ProviderBindingOptions(lifetime=Transient())],
    )
    def resolved(
        self,
        request: pytest.FixtureRequest,
        container: Container,
        scope: Scope,
        provider: Mock,
    ) -> FakeService:
        container.register(FakeService).factory(provider, **request.param)

        return scope.resolve(FakeService)

    def test_calls_and_returns_binding_provider_result_on_each_resolve(
        self, resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(scope), call(scope)])

    def test_calls_and_returns_binding_provider_result_on_different_scope(
        self, resolved: FakeService, container: Container, scope: Scope, provider: Mock
    ) -> None:
        with Scope(container) as scope2:
            received = scope2.resolve(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(scope), call(scope2)])

    def test_release_scope_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        another = scope.resolve(FakeService)

        scope.release()

        assert resolved.exited
        assert another.exited


class TestResolveTypeBoundToSingletonBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, container: Container, scope: Scope, provider: Mock
    ) -> FakeService:
        container.register(FakeService).factory(provider, lifetime=Singleton())

        return scope.resolve(FakeService)

    def test_calls_and_returns_binding_provider_result_once_per_scope(
        self, resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is resolved
        provider.assert_called_once_with(scope)

    def test_calls_and_returns_binding_provider_result_once_accross_scopes(
        self,
        resolved: FakeService,
        container: Container,
        scope: Container,
        provider: Mock,
    ) -> None:
        with Scope(container) as scope2:
            received = scope2.resolve(FakeService)

        assert received is resolved
        provider.assert_called_once_with(scope)

    def test_release_scope_not_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.release()

        assert not resolved.exited

    def test_release_container_exit_entered_context_manager(
        self, container: Container, resolved: FakeService
    ) -> None:
        container.release()

        assert resolved.exited

    def test_release_container_clear_cached_value(
        self, container: Container, scope: Scope, resolved: FakeService
    ) -> None:
        container.release()

        received = scope.resolve(FakeService)

        assert received is not resolved

    def test_release_scope_not_clear_cached_value(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.release()

        received = scope.resolve(FakeService)

        assert received is resolved


class TestResolveTypeBoundToScopedBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, container: Container, scope: Scope, provider: Mock
    ) -> FakeService:
        container.register(FakeService).factory(provider, lifetime=Scoped())

        return scope.resolve(FakeService)

    def test_calls_and_returns_binding_provider_result_once_per_scope(
        self, resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        received = scope.resolve(FakeService)

        assert received is resolved
        provider.assert_called_once_with(scope)

    def test_calls_and_returns_binding_provider_result_on_different_scope(
        self, resolved: FakeService, container: Container, scope: Scope, provider: Mock
    ) -> None:
        with Scope(container) as scope2:
            received = scope2.resolve(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(scope), call(scope2)])

    def test_release_scope_exit_entered_context_manager(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.release()

        assert resolved.exited

    def test_release_scope_clear_cached_value(
        self, scope: Scope, resolved: FakeService
    ) -> None:
        scope.release()

        received = scope.resolve(FakeService)

        assert received is not resolved
