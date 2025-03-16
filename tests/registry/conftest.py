import pytest

from handless import Registry


@pytest.fixture
def sut() -> Registry:
    return Registry()
