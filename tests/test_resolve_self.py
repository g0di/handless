from typing import TypedDict

import pytest

from handless import Container, LifetimeLiteral, Registry, Scope
from tests.helpers import (
    FakeService,
    FakeServiceWithParams,
    FakeServiceWithUntypedParams,
)


class SelfBindingOptions(TypedDict, total=False):
    enter: bool
    lifetime: LifetimeLiteral


def test_can_not_bind_type_with_untyped_parameters_to_self(registry: Registry) -> None:
    with pytest.raises(TypeError):
        registry.bind(FakeServiceWithUntypedParams).to_self()


def test_resolve_self_binding_calls_constructor_and_returns_created_instance(
    registry: Registry, container: Container
) -> None:
    registry.bind(FakeService).to_self()

    resolved = container.get(FakeService)

    assert isinstance(resolved, FakeService)


@pytest.mark.parametrize(
    "options", [SelfBindingOptions(), SelfBindingOptions(enter=True)]
)
def test_resolve_self_binding_enters_context_manager(
    registry: Registry, container: Container, options: SelfBindingOptions
) -> None:
    registry.bind(FakeService).to_self(**options)

    resolved = container.get(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_self_binding_not_enter_context_manager_when_enter_is_false(
    registry: Registry, container: Container
) -> None:
    registry.bind(FakeService).to_self(enter=False)

    resolved = container.get(FakeService)

    assert not resolved.entered


def test_resolve_self_binding_not_enter_non_context_manager_objects(
    registry: Registry, container: Container
) -> None:
    registry.bind(object).to_self(enter=True)

    try:
        container.get(FakeService)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


# test resolve self calls constructor, and not enters context manager if enter is false
def test_resolve_self_binding_resolve_type_parameters_first(
    registry: Registry, container: Container
) -> None:
    registry.bind(int).to_value(42)
    registry.bind(str).to_provider(lambda: "Foo!")
    registry.bind(FakeServiceWithParams).to_self()

    resolved = container.get(FakeServiceWithParams)

    assert resolved.foo == "Foo!"
    assert resolved.bar == 42  # noqa: PLR2004


class TestResolveTransientSelfBinding:
    @pytest.fixture(
        autouse=True,
        params=[SelfBindingOptions(), SelfBindingOptions(lifetime="transient")],
    )
    def resolved(
        self, request: pytest.FixtureRequest, registry: Registry, container: Container
    ) -> FakeService:
        registry.bind(FakeService).to_self(**request.param)

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_creates_a_new_instance_on_each_resolve(
        self, resolved: FakeService, container: Container
    ) -> None:
        resolved2 = container.get(FakeService)

        assert resolved2 is not resolved

    def test_creates_a_new_instance_for_another_container(
        self, resolved: FakeService, registry: Registry
    ) -> None:
        container2 = Container(registry)
        resolved2 = container2.get(FakeService)

        assert resolved2 is not resolved

    def test_creates_a_new_instance_for_a_scope(
        self, resolved: FakeService, scope_resolved: FakeService
    ) -> None:
        assert scope_resolved is not resolved

    def test_creates_a_new_instance_for_each_resolve_in_a_scope(
        self, scope_resolved: FakeService, scope: Scope
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved is not scope_resolved2


class TestResolveSingletonSelfBinding:
    @pytest.fixture(autouse=True)
    def resolved(self, registry: Registry, container: Container) -> FakeService:
        registry.bind(FakeService).to_self(lifetime="singleton")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_cache_instance_per_container(
        self, resolved: FakeService, container: Container
    ) -> None:
        resolved2 = container.get(FakeService)

        assert resolved2 is resolved

    def test_creates_a_new_instance_for_another_container(
        self, resolved: FakeService, registry: Registry
    ) -> None:
        container2 = Container(registry)
        resolved2 = container2.get(FakeService)

        assert resolved2 is not resolved

    def test_use_cached_instance_for_scope(
        self, resolved: FakeService, scope_resolved: FakeService
    ) -> None:
        assert scope_resolved is resolved

    def test_use_cached_instance_within_scope(
        self, scope_resolved: FakeService, scope: Scope
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved is scope_resolved2


class TestResolveScopedSelfBinding:
    @pytest.fixture(autouse=True)
    def resolved(self, registry: Registry, container: Container) -> FakeService:
        registry.bind(FakeService).to_self(lifetime="scoped")

        return container.get(FakeService)

    @pytest.fixture
    def scope_resolved(self, scope: Scope) -> FakeService:
        return scope.get(FakeService)

    def test_cache_instance_per_container(
        self, resolved: FakeService, container: Container
    ) -> None:
        resolved2 = container.get(FakeService)

        assert resolved2 is resolved

    def test_creates_a_new_instance_for_another_container(
        self, resolved: FakeService, registry: Registry
    ) -> None:
        container2 = Container(registry)
        resolved2 = container2.get(FakeService)

        assert resolved2 is not resolved

    def test_creates_a_new_instance_per_scope(
        self, resolved: FakeService, scope_resolved: FakeService
    ) -> None:
        assert scope_resolved is not resolved

    def test_use_cached_instance_within_scope(
        self, scope_resolved: FakeService, scope: Scope
    ) -> None:
        scope_resolved2 = scope.get(FakeService)

        assert scope_resolved is scope_resolved2
