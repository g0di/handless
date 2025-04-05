import pytest

from handless import Container, Registry
from tests.helpers import FakeService


@pytest.fixture
def sut() -> Container:
    return Registry().register(FakeService, lifetime="transient").create_container()


def test_resolve_type_binded_to_transient_factory_calls_factory_each_time(
    sut: Container,
) -> None:
    v1 = sut.resolve(FakeService)
    v2 = sut.resolve(FakeService)

    assert v1 is not v2


def test_resolve_type_binded_to_transient_factory_from_scope_calls_factory_each_time(
    sut: Container,
) -> None:
    scope = sut.create_scope()

    v1 = sut.resolve(FakeService)
    v2 = sut.resolve(FakeService)
    v3 = scope.resolve(FakeService)
    v4 = scope.resolve(FakeService)

    assert v1 is not v2 is not v3 is not v4


def test_resolve_type_binded_to_transient_factory_with_context_manager_are_exited_on_scope_close(
    sut: Container,
) -> None:
    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited
