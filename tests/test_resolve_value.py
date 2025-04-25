from contextlib import nullcontext
from typing import TypedDict

import pytest

from handless import Container, Registry, Scope
from tests.helpers import FakeContextManager, FakeService


class ValueOptions(TypedDict, total=False):
    enter: bool


class TestResolveValue:
    @pytest.fixture
    def expected(self) -> FakeService:
        return FakeService()

    @pytest.fixture(
        autouse=True,
        name="resolved",
        params=[ValueOptions(), ValueOptions(enter=False)],
    )
    def resolve_value(
        self,
        request: pytest.FixtureRequest,
        registry: Registry,
        container: Container,
        expected: FakeService,
    ) -> FakeService:
        registry.bind(FakeService).to_value(expected, **request.param)

        return container.get(FakeService)

    def test_returns_registered_value(
        self, resolved: FakeService, expected: FakeService
    ) -> None:
        assert resolved is expected

    def test_always_returns_registered_value(
        self, container: Container, expected: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is expected

    def test_all_containers_returns_registered_value(
        self, registry: Registry, expected: FakeService
    ) -> None:
        container2 = Container(registry)
        another = container2.get(FakeService)

        assert another is expected

    def test_value_context_manager_is_not_entered(self, resolved: FakeService) -> None:
        assert not resolved.entered


class TestResolveValueWithContextManager:
    @pytest.fixture
    def expected(self) -> FakeService:
        return FakeService()

    @pytest.fixture
    def cm(self, expected: FakeService) -> FakeContextManager:
        return FakeContextManager(expected)

    @pytest.fixture(autouse=True, name="resolved")
    def resolve_value(
        self, registry: Registry, container: Container, cm: FakeContextManager
    ) -> FakeService:
        registry.bind(FakeService).to_value(cm, enter=True)

        return container.get(FakeService)

    def test_returns_value_returned_by_context_manager(
        self, resolved: FakeService, expected: FakeService
    ) -> None:
        assert resolved is expected

    def test_not_reenter_context_manager(
        self, container: Container, cm: FakeContextManager, expected: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is expected
        assert not cm.reentered

    def test_not_exit_context_manager_imediately(self, cm: FakeContextManager) -> None:
        assert not cm.exited

    def test_context_manager_is_exited_on_container_close(
        self, container: Container, cm: FakeContextManager
    ) -> None:
        container.close()

        assert cm.exited

    def test_context_manager_is_not_exited_on_scope_close(
        self, scope: Scope, cm: FakeContextManager
    ) -> None:
        scope.close()

        assert not cm.exited


def test_register_value_without_context_manager_and_enter_true_do_not_try_to_enter_context(
    registry: Registry, container: Container
) -> None:
    expected = object()
    registry.bind(object).to_value(expected, enter=True)

    resolved = container.get(object)

    assert resolved is expected


def test_register_value_with_context_manager_of_different_type_and_enter_false_is_not_allowed(
    registry: Registry,
) -> None:
    registry.bind(str).to_value(nullcontext("Hello World!"), enter=False)  # type: ignore[call-overload]
