from collections.abc import Iterator

import pytest

from handless import Container, Scope

pytest.register_assert_rewrite("tests.helpers")


@pytest.fixture
def container() -> Iterator[Container]:
    with Container() as container:
        yield container


@pytest.fixture
def scope(container: Container) -> Iterator[Scope]:
    with Scope(container) as scp:
        yield scp
