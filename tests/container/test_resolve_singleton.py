import pytest

from handless import Container, Registry
from tests.helpers import FakeService


@pytest.fixture
def sut() -> Container:
    return Registry().register_singleton(FakeService).create_container()


def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value(
    sut: Container,
) -> None:
    v1 = sut.resolve(FakeService)
    v2 = sut.resolve(FakeService)

    assert v1 is v2


def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value_accross_scopes(
    sut: Container,
) -> None:
    scope = sut.create_scope()

    v1 = sut.resolve(FakeService)
    v2 = sut.resolve(FakeService)
    v3 = scope.resolve(FakeService)
    v4 = scope.resolve(FakeService)

    assert v1 is v2 is v3 is v4


def test_singletons_are_cleared_on_container_clear(sut: Container) -> None:
    v1 = sut.resolve(FakeService)

    sut.clear()

    v2 = sut.resolve(FakeService)

    assert v1 is not v2


def test_singletons_are_not_cleared_on_scope_clear(sut: Container) -> None:
    scope = sut.create_scope()
    v1 = scope.resolve(FakeService)

    scope.clear()

    v2 = sut.resolve(FakeService)

    assert v1 is v2
