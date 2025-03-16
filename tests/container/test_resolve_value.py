import pytest

from handless import Container, Registry
from tests.helpers import FakeService


@pytest.fixture
def value() -> FakeService:
    return FakeService()


@pytest.fixture
def sut(value: FakeService) -> Container:
    return Registry().register_value(FakeService, value).create_container()


def test_resolve_a_value_descriptor_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    resolved = sut.resolve(FakeService)
    resolved2 = sut.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_descriptor_from_scoped_container_returns_the_value(
    sut: Container, value: FakeService
) -> None:
    scope = sut.create_scope()

    resolved = sut.resolve(FakeService)
    resolved2 = scope.resolve(FakeService)

    assert resolved is value
    assert resolved2 is value


def test_resolve_a_value_descriptor_do_not_enter_cm_by_default(sut: Container) -> None:
    resolved = sut.resolve(FakeService)

    assert resolved.entered is False
    assert resolved.exited is False


def test_resolve_a_value_descriptor_with_enter_true_enters_cm() -> None:
    sut = (
        Registry()
        .register_value(FakeService, FakeService(), enter=True)
        .create_container()
    )
    resolved = sut.resolve(FakeService)

    assert resolved.entered is True
