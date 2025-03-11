import pytest

from handless import Registry, Value
from tests.helpers import FakeService
from tests.test_context_managers import FakeServiceWithContextManager


@pytest.fixture
def expected() -> FakeService:
    return FakeService()


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_explicit_value_resolves_with_given_value(
    registry: Registry,
    expected: FakeService,
) -> None:
    container = registry.register_value(FakeService, expected).create_container()

    received = container.resolve(FakeService)

    assert received is expected


def test_register_implicit_value_resolves_with_given_value(
    registry: Registry,
    expected: FakeService,
) -> None:
    container = registry.register(FakeService, expected).create_container()

    received = container.resolve(FakeService)

    assert received is expected


def test_register_value_descriptor_resolves_with_given_value(
    registry: Registry,
    expected: FakeService,
) -> None:
    container = registry.register(FakeService, Value(expected)).create_container()

    received = container.resolve(FakeService)

    assert received is expected


def test_set_value_resolves_with_given_value(
    registry: Registry,
    expected: FakeService,
) -> None:
    registry[FakeService] = expected
    container = registry.create_container()

    received = container[FakeService]

    assert received is expected


def test_set_value_descriptor_resolves_with_given_value(
    registry: Registry,
    expected: FakeService,
) -> None:
    registry[FakeService] = Value(expected)
    container = registry.create_container()

    received = container[FakeService]

    assert received is expected


def test_resolve_context_manager_value_is_not_entered_by_default(
    registry: Registry,
) -> None:
    container = registry.register_value(
        FakeServiceWithContextManager, FakeServiceWithContextManager()
    ).create_container()

    received = container[FakeServiceWithContextManager]

    assert not received.entered
