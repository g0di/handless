from unittest.mock import Mock, create_autospec

import pytest

from handless import Registry
from handless.exceptions import ResolveError
from tests.helpers import FakeService


def test_resolve_type_binded_to_scoped_factory_from_root_container_raise_an_error() -> (
    None
):
    mock_factory: Mock = create_autospec(lambda: FakeService())
    container = (
        Registry()
        .register(FakeService, mock_factory, lifetime="scoped")
        .create_container()
    )

    with pytest.raises(ResolveError):
        container.resolve(FakeService)

    mock_factory.assert_not_called()


def test_resolve_type_binded_to_scoped_factory_cache_returned_value_per_scope() -> None:
    registry = Registry().register(FakeService, lifetime="scoped")
    container = registry.create_container()
    scope1 = container.create_scope()
    scope2 = container.create_scope()

    v1 = scope1.resolve(FakeService)
    v2 = scope1.resolve(FakeService)
    v3 = scope2.resolve(FakeService)
    v4 = scope2.resolve(FakeService)

    assert v1 is v2
    assert v3 is v4
    assert v1 is not v3


def test_resolve_type_binded_to_scoped_factory_is_cleared_on_scope_close() -> None:
    sut = (
        Registry()
        .register(FakeService, lifetime="scoped")
        .create_container()
        .create_scope()
    )
    v1 = sut.resolve(FakeService)

    sut.close()

    v2 = sut.resolve(FakeService)

    assert v1 is not v2


def test_resolve_type_binded_to_scoped_factory_with_context_manager_is_exited_on_close() -> (
    None
):
    sut = (
        Registry()
        .register(FakeService, lifetime="scoped")
        .create_container()
        .create_scope()
    )

    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited
