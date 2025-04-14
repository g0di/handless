import pytest

from handless import Container


@pytest.fixture
def sut(container: Container) -> Container:
    return container
