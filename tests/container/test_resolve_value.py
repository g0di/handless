import pytest

from handless import Container, Registry
from tests.helpers import FakeService


@pytest.fixture
def value() -> FakeService:
    return FakeService()


@pytest.fixture(autouse=True)
def setup_registry(
    registry: Registry, value: FakeService, request: pytest.FixtureRequest
) -> None:
    enter_mark: pytest.Mark | None = request.node.get_closest_marker("enter")
    registry.register(FakeService).value(
        value, enter=bool(enter_mark.args[0]) if enter_mark else False
    )


def test_resolve_a_value_binding_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    resolved = sut.resolve(FakeService)
    resolved2 = sut.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_binding_from_scoped_container_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    scope = sut.create_scope()

    resolved = sut.resolve(FakeService)
    resolved2 = scope.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_binding_do_not_enter_cm_by_default(sut: Container) -> None:
    resolved = sut.resolve(FakeService)

    assert resolved.entered is False
    assert resolved.exited is False


@pytest.mark.enter(True)
def test_resolve_a_value_binding_with_enter_true_enters_context_manager(
    sut: Container,
) -> None:
    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


@pytest.mark.enter(True)
def test_resolve_a_value_binding_with_enter_true_enters_context_manager_only_once(
    sut: Container,
) -> None:
    scope = sut.create_scope()

    resolved = sut.resolve(FakeService)
    scope.resolve(FakeService)

    assert not resolved.reentered


@pytest.mark.enter(True)
def test_close_container_exit_entered_value_binding_context_manager(
    sut: Container,
) -> None:
    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited


@pytest.mark.enter(True)
def test_close_scope_not_exit_entered_value_binding_context_manager(
    sut: Container,
) -> None:
    scope = sut.create_scope()
    resolved = scope.resolve(FakeService)

    scope.close()

    assert not resolved.exited
