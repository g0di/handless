from unittest.mock import Mock, create_autospec

import pytest

from handless import Container, Registry
from handless.exceptions import ResolveError
from tests.helpers import FakeService


def test_resolve_type_binded_to_scoped_factory_from_root_container_raise_an_error(
    sut: Container, registry: Registry
) -> None:
    mock_factory: Mock = create_autospec(lambda: FakeService())
    registry.bind(FakeService).to_factory(mock_factory, lifetime="scoped")

    with pytest.raises(ResolveError):
        sut.resolve(FakeService)

    mock_factory.assert_not_called()


def test_resolve_type_binded_to_scoped_factory_cache_returned_value_per_scope(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self(lifetime="scoped")
    scope1 = sut.create_scope()
    scope2 = sut.create_scope()

    v1 = scope1.resolve(FakeService)
    v2 = scope1.resolve(FakeService)
    v3 = scope2.resolve(FakeService)
    v4 = scope2.resolve(FakeService)

    assert v1 is v2
    assert v3 is v4
    assert v1 is not v3


def test_resolve_type_binded_to_scoped_factory_is_cleared_on_scope_close(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self(lifetime="scoped")
    scope = sut.create_scope()
    v1 = scope.resolve(FakeService)

    scope.close()

    v2 = scope.resolve(FakeService)

    assert v1 is not v2


def test_resolve_type_binded_to_scoped_factory_with_context_manager_is_exited_on_close(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self(lifetime="scoped")
    scope = sut.create_scope()

    resolved = scope.resolve(FakeService)

    scope.close()

    assert resolved.exited
