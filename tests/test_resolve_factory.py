from typing import TypedDict
from unittest.mock import Mock, call

import pytest

from handless import Container, LifetimeLiteral, Registry, Scope
from tests.helpers import FakeService


class FactoryBindingOptions(TypedDict, total=False):
    enter: bool
    lifetime: LifetimeLiteral


def test_resolve_factory_binding_calls_factory_and_returns_its_result(
    registry: Registry, container: Container
) -> None:
    expected = FakeService()
    factory = Mock(wraps=lambda _: expected)
    registry.bind(FakeService).to_factory(factory)

    resolved = container.get(FakeService)

    assert resolved is expected
    factory.assert_called_once_with(container)


@pytest.mark.parametrize(
    "options", [FactoryBindingOptions(), FactoryBindingOptions(enter=True)]
)
def test_resolve_factory_binding_enters_context_manager(
    registry: Registry, container: Container, options: FactoryBindingOptions
) -> None:
    registry.bind(FakeService).to_factory(lambda _: FakeService(), **options)

    resolved = container.get(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_factory_binding_not_enter_context_manager_when_enter_is_false(
    registry: Registry, container: Container
) -> None:
    registry.bind(FakeService).to_factory(lambda _: FakeService(), enter=False)

    resolved = container.get(FakeService)

    assert not resolved.entered


def test_resolve_factory_binding_not_enter_non_context_manager_objects(
    registry: Registry, container: Container
) -> None:
    registry.bind(object).to_factory(lambda _: object(), enter=True)

    try:
        container.get(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


# test resolve self calls constructor, and not enters context manager if enter is false
def test_resolve_factory_binding_inject_current_container_as_first_parameter(
    registry: Registry, container: Container
) -> None:
    registry.bind(int).to_value(42)
    registry.bind(str).to_factory(lambda c: f"Foo!{c.get(int)}")

    resolved = container.get(str)

    assert resolved == "Foo!42"


class TestResolveTransientFactoryBinding:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(
        autouse=True,
        params=[FactoryBindingOptions(), FactoryBindingOptions(lifetime="transient")],
    )
    def resolved(
        self,
        request: pytest.FixtureRequest,
        registry: Registry,
        container: Container,
        factory: Mock,
    ) -> FakeService:
        registry.bind(FakeService).to_factory(factory, **request.param)

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_returns_factory_result_on_each_resolve(
        self, resolved: FakeService, container: Container, factory: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(container), call(container)])

    def test_returns_factory_result_for_another_container(
        self,
        resolved: FakeService,
        registry: Registry,
        factory: Mock,
        container: Container,
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(container), call(container2)])

    def test_returns_factory_result_for_a_scope(
        self,
        resolved: FakeService,
        scope: Scope,
        scope_resolved: FakeService,
        factory: Mock,
        container: Container,
    ) -> None:
        assert resolved is not scope_resolved
        factory.assert_has_calls([call(container), call(scope)])

    def test_returns_factory_result_for_each_resolve_in_a_scope(
        self,
        scope_resolved: FakeService,
        scope: Scope,
        factory: Mock,
        container: Container,
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is not scope_resolved
        factory.assert_has_calls([call(container), call(scope), call(scope)])


class TestResolveSingletonFactoryBinding:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, registry: Registry, container: Container, factory: Mock
    ) -> FakeService:
        registry.bind(FakeService).to_factory(factory, lifetime="singleton")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_returns_cached_factory_result_on_successive_resolve(
        self, resolved: FakeService, container: Container, factory: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is resolved
        factory.assert_called_once_with(container)

    def test_returns_cached_factory_result_per_container(
        self,
        resolved: FakeService,
        registry: Registry,
        factory: Mock,
        container: Container,
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(container), call(container2)])

    def test_returns_cached_factory_result_on_scope(
        self,
        resolved: FakeService,
        scope_resolved: FakeService,
        factory: Mock,
        container: Container,
    ) -> None:
        assert resolved is scope_resolved
        factory.assert_called_once_with(container)

    def test_returns_cached_factory_result_on_scope_successive_resolve(
        self,
        scope_resolved: FakeService,
        scope: Scope,
        factory: Mock,
        container: Container,
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is scope_resolved
        factory.assert_called_once_with(container)


class TestResolveScopedSelfBinding:
    @pytest.fixture
    def factory(self) -> Mock:
        return Mock(wraps=lambda _: FakeService())

    @pytest.fixture(autouse=True)
    def resolved(
        self, registry: Registry, container: Container, factory: Mock
    ) -> FakeService:
        registry.bind(FakeService).to_factory(factory, lifetime="scoped")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_returns_cached_factory_result_on_successive_resolve(
        self, resolved: FakeService, container: Container, factory: Mock
    ) -> None:
        received = container.get(FakeService)

        assert received is resolved
        factory.assert_called_once_with(container)

    def test_returns_cached_factory_result_per_container(
        self,
        resolved: FakeService,
        registry: Registry,
        factory: Mock,
        container: Container,
    ) -> None:
        container2 = Container(registry)
        received = container2.get(FakeService)

        assert received is not resolved
        factory.assert_has_calls([call(container), call(container2)])

    def test_returns_cached_factory_result_per_scope(
        self,
        resolved: FakeService,
        scope_resolved: FakeService,
        factory: Mock,
        container: Container,
        scope: Scope,
    ) -> None:
        assert resolved is not scope_resolved
        factory.assert_has_calls([call(container), call(scope)])

    def test_returns_cached_factory_result_on_scope_successive_resolve(
        self,
        scope_resolved: FakeService,
        scope: Scope,
        factory: Mock,
        container: Container,
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved2 is scope_resolved
        # One call on the container itself on fixture, and another one for the scope
        factory.assert_has_calls([call(container), call(scope)])
