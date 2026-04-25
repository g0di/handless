from collections.abc import AsyncIterator, Iterator
from typing import Literal

import pytest

from handless import Container, Scope

pytest.register_assert_rewrite("tests.helpers")


@pytest.fixture(scope="session")
def anyio_backend() -> Literal["asyncio"]:
    return "asyncio"


@pytest.fixture
def container() -> Iterator[Container]:
    with Container() as container:
        yield container


@pytest.fixture
def context(container: Container) -> Iterator[Scope]:
    with container.create_scope() as ctx:
        yield ctx


@pytest.fixture
async def acontainer() -> AsyncIterator[Container]:
    async with Container() as container:
        yield container


@pytest.fixture
async def acontext(acontainer: Container) -> AsyncIterator[Scope]:
    async with acontainer.create_scope() as ctx:
        yield ctx
