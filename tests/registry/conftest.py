import pytest

from handless import Registry


@pytest.fixture
def sut(registry: Registry) -> Registry:
    return registry
