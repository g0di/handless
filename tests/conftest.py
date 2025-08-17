from collections.abc import Iterator
from typing import Literal

import pytest

from handless import Container, ResolutionContext

pytest.register_assert_rewrite("tests.helpers")


@pytest.fixture(scope="session")
def anyio_backend() -> Literal["asyncio"]:
    return "asyncio"


@pytest.fixture
def container() -> Iterator[Container]:
    with Container() as container:
        yield container


@pytest.fixture
def context(container: Container) -> Iterator[ResolutionContext]:
    with container.open_context() as ctx:
        yield ctx
