from typing import TypedDict
from unittest.mock import Mock, call

import pytest

from handless import Container, LifetimeLiteral, Registry, Scope
from tests.helpers import (
    FakeService,
    FakeServiceWithParams,
    fake_service_factory_with_params,
    fake_service_factory_with_untyped_params,
)


class ProviderBindingOptions(TypedDict, total=False):
    enter: bool
    lifetime: LifetimeLiteral


def test_can_not_bind_type_with_untyped_parameters_to_self(registry: Registry) -> None:
    with pytest.raises(TypeError):
        registry.bind(FakeServiceWithParams).to_provider(
            fake_service_factory_with_untyped_params
        )


def test_resolve_provider_binding_calls_provider_and_returns_created_instance(
    registry: Registry, container: Container
) -> None:
    provider = Mock(return_value=(expected := FakeService()))
    registry.bind(FakeService).to_provider(provider)

    resolved = container.get(FakeService)

    assert resolved is expected
    provider.assert_called_once_with()


@pytest.mark.parametrize(
    "options", [ProviderBindingOptions(), ProviderBindingOptions(enter=True)]
)
def test_resolve_provider_binding_enters_context_manager(
    registry: Registry, container: Container, options: ProviderBindingOptions
) -> None:
    registry.bind(FakeService).to_provider(lambda: FakeService(), **options)

    resolved = container.get(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_provider_binding_not_enter_context_manager_when_enter_is_false(
    registry: Registry, container: Container
) -> None:
    registry.bind(FakeService).to_provider(lambda: FakeService(), enter=False)

    resolved = container.get(FakeService)

    assert not resolved.entered


# test resolve self calls constructor, and not enters context manager if enter is false
def test_resolve_provide_binding_resolve_parameters_first(
    registry: Registry, container: Container
) -> None:
    registry.bind(int).to_value(42)
    registry.bind(str).to_provider(lambda: "Foo!")
    registry.bind(FakeServiceWithParams).to_provider(fake_service_factory_with_params)

    resolved = container.get(FakeServiceWithParams)

    assert resolved.foo == "Foo!"
    assert resolved.bar == 42  # noqa: PLR2004


class TestResolveTransientProviderBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(side_effect=FakeService)

    @pytest.fixture(
        autouse=True,
        params=[ProviderBindingOptions(), ProviderBindingOptions(lifetime="transient")],
    )
    def resolved(
        self,
        request: pytest.FixtureRequest,
        registry: Registry,
        container: Container,
        provider: Mock,
    ) -> FakeService:
        registry.bind(FakeService).to_provider(provider, **request.param)

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_creates_a_new_instance_on_each_resolve(
        self, resolved: FakeService, container: Container, provider: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(), call()])

    def test_creates_a_new_instance_for_another_container(
        self, resolved: FakeService, registry: Registry, provider: Mock
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(), call()])

    def test_creates_a_new_instance_for_a_scope(
        self, resolved: FakeService, scope_resolved: FakeService, provider: Mock
    ) -> None:
        assert resolved is not scope_resolved
        provider.assert_has_calls([call(), call()])

    def test_creates_a_new_instance_for_each_resolve_in_a_scope(
        self, scope_resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is not scope_resolved
        provider.assert_has_calls([call(), call(), call()])


class TestResolveSingletonProviderBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(side_effect=FakeService)

    @pytest.fixture(autouse=True)
    def resolved(
        self, registry: Registry, container: Container, provider: Mock
    ) -> FakeService:
        registry.bind(FakeService).to_provider(provider, lifetime="singleton")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_reuse_cached_provider_return_value_on_successive_resolve(
        self, resolved: FakeService, container: Container, provider: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is resolved
        provider.assert_called_once_with()

    def test_cache_provider_return_value_per_container(
        self, resolved: FakeService, registry: Registry, provider: Mock
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(), call()])

    def test_reuse_cached_provider_return_value_on_scope(
        self, resolved: FakeService, scope_resolved: FakeService, provider: Mock
    ) -> None:
        assert resolved is scope_resolved
        provider.assert_called_once_with()

    def test_reuse_cached_provider_return_value_on_scope_successive_resolve(
        self, scope_resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is scope_resolved
        provider.assert_called_once_with()


class TestResolveScopedSelfBinding:
    @pytest.fixture
    def provider(self) -> Mock:
        return Mock(side_effect=FakeService)

    @pytest.fixture(autouse=True)
    def resolved(
        self, registry: Registry, container: Container, provider: Mock
    ) -> FakeService:
        registry.bind(FakeService).to_provider(provider, lifetime="scoped")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_reuse_cached_provider_return_value_on_successive_resolve(
        self, resolved: FakeService, container: Container, provider: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is resolved
        provider.assert_called_once_with()

    def test_cache_provider_return_value_per_container(
        self, resolved: FakeService, registry: Registry, provider: Mock
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        provider.assert_has_calls([call(), call()])

    def test_cache_provider_return_value_per_scope(
        self, resolved: FakeService, scope_resolved: FakeService, provider: Mock
    ) -> None:
        assert resolved is not scope_resolved
        provider.assert_has_calls([call(), call()])

    def test_reuse_cached_provider_return_value_on_scope_successive_resolve(
        self, scope_resolved: FakeService, scope: Scope, provider: Mock
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is scope_resolved
        # One call on the container itself on fixture, and another one for the scope
        provider.assert_has_calls([call(), call()])
