from collections.abc import AsyncIterator, Iterator
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


@pytest.fixture
async def acontainer() -> AsyncIterator[Container]:
    async with Container() as container:
        yield container


@pytest.fixture
async def acontext(acontainer: Container) -> AsyncIterator[ResolutionContext]:
    async with acontainer.open_context() as ctx:
        yield ctx
