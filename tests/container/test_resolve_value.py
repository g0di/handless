import pytest

from handless import Container, Registry
from tests.helpers import FakeService


@pytest.fixture
def value() -> FakeService:
    return FakeService()


@pytest.fixture
def sut(value: FakeService) -> Container:
    return Registry().register(FakeService, value).create_container()


def test_resolve_a_value_provider_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    resolved = sut.resolve(FakeService)
    resolved2 = sut.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_provider_from_scoped_container_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    scope = sut.create_scope()

    resolved = sut.resolve(FakeService)
    resolved2 = scope.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_provider_do_not_enter_cm_by_default(sut: Container) -> None:
    resolved = sut.resolve(FakeService)

    assert resolved.entered is False
    assert resolved.exited is False


def test_resolve_a_value_provider_with_enter_true_enters_context_manager() -> None:
    sut = Registry().register(FakeService, FakeService(), enter=True).create_container()

    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_a_value_provider_with_enter_true_enters_context_manager_only_once() -> (
    None
):
    sut = Registry().register(FakeService, FakeService(), enter=True).create_container()
    scope = sut.create_scope()

    resolved = sut.resolve(FakeService)
    scope.resolve(FakeService)

    assert not resolved.reentered


def test_close_container_exit_entered_value_provider_context_manager() -> None:
    sut = Registry().register(FakeService, FakeService(), enter=True).create_container()
    resolved = sut.resolve(FakeService)
    sut.close()

    assert resolved.exited


def test_close_scope_not_exit_entered_value_provider_context_manager() -> None:
    sut = (
        Registry()
        .register(FakeService, FakeService(), enter=True)
        .create_container()
        .create_scope()
    )
    resolved = sut.resolve(FakeService)
    sut.close()

    assert not resolved.exited
