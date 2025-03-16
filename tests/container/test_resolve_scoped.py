from unittest.mock import Mock, create_autospec

import pytest

from handless import Registry
from handless.exceptions import ServiceResolveError
from tests.helpers import FakeService


def test_resolve_a_scoped_factory_descriptor_from_root_container_raise_an_error() -> (
    None
):
    mock_factory: Mock = create_autospec(lambda: FakeService())
    container = Registry().register_scoped(FakeService, mock_factory).create_container()

    with pytest.raises(ServiceResolveError):
        container.resolve(FakeService)

    mock_factory.assert_not_called()


def test_resolve_a_scoped_factory_descriptor_calls_and_cache_factory_returned_value_per_scope() -> (
    None
):
    registry = Registry().register_scoped(FakeService)
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
