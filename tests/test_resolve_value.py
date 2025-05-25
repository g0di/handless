from contextlib import nullcontext
from typing import TypedDict

import pytest

from handless import Container, Registry, Scope
from tests.helpers import FakeContextManager, FakeService


class ValueOptions(TypedDict, total=False):
    enter: bool


class TestResolveValueBinding:
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

    def test_returns_given_value(
        self, resolved: FakeService, expected: FakeService
    ) -> None:
        assert resolved is expected

    def test_always_returns_given_value(
        self, container: Container, expected: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is expected

    def test_returns_given_value_for_any_container(
        self, registry: Registry, expected: FakeService
    ) -> None:
        container2 = Container(registry)
        another = container2.get(FakeService)

        assert another is expected

    def test_not_enter_context_manager_by_default(self, resolved: FakeService) -> None:
        assert not resolved.entered


class TestResolveValueBindingWithContextManager:
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

    def test_returns_results_of_context_manager(
        self, resolved: FakeService, expected: FakeService
    ) -> None:
        assert resolved is expected

    def test_not_reenter_context_manager(
        self, container: Container, cm: FakeContextManager, expected: FakeService
    ) -> None:
        another = container.get(FakeService)

        assert another is expected
        assert not cm.reentered

    def test_not_exit_context_manager(self, cm: FakeContextManager) -> None:
        assert not cm.exited

    def test_exits_context_manager_on_container_close(
        self, container: Container, cm: FakeContextManager
    ) -> None:
        container.close()

        assert cm.exited

    def test_not_exits_context_manager_on_scope_close(
        self, scope: Scope, cm: FakeContextManager
    ) -> None:
        scope.close()

        assert not cm.exited


def test_resolve_value_binding_not_enter_non_context_manager_objects(
    registry: Registry, container: Container
) -> None:
    registry.bind(object).to_value(object(), enter=True)

    try:
        container.get(object)
    except AttributeError:
        pytest.fail(reason="Should not try to enter non context manager object")


def test_bind_to_value_with_context_manager_of_different_type_and_enter_false_is_not_allowed(
    registry: Registry,
) -> None:
    # Just check typings here
    registry.bind(str).to_value(nullcontext("Hello World!"), enter=False)  # type: ignore[call-overload]
