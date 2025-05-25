from unittest.mock import Mock, call

import pytest

from handless import Container, Registry
from tests.helpers import FakeService, IFakeService


@pytest.fixture
def expected() -> FakeService:
    return FakeService()


@pytest.fixture
def factory(expected: FakeService) -> Mock:
    return Mock(wraps=lambda: expected)


@pytest.fixture(autouse=True, name="resolved")
def get_alias_binding_result(
    registry: Registry, container: Container, factory: Mock
) -> IFakeService:
    registry.bind(FakeService).to_provider(factory)
    registry.bind(IFakeService).to(FakeService)  # type: ignore[type-abstract]

    return container.get(IFakeService)  # type: ignore[type-abstract]


def test_calls_alias_provider(factory: Mock) -> None:
    factory.assert_called_once()


def test_returns_alias_provider_result(
    resolved: IFakeService, expected: FakeService
) -> None:
    assert resolved is expected


def test_not_reenter_context_manager(resolved: FakeService) -> None:
    assert resolved.entered
    assert not resolved.reentered


def test_calls_alias_provider_on_each_resolve(
    container: Container, factory: Mock
) -> None:
    container.get(IFakeService)  # type: ignore[type-abstract]

    factory.assert_has_calls([call(), call()])


def test_calls_alias_provider_on_scope_resolve(
    container: Container, factory: Mock
) -> None:
    scope = container.create_scope()
    scope.get(IFakeService)  # type: ignore[type-abstract]

    factory.assert_has_calls([call(), call()])
