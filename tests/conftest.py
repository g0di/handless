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
def scope(container: Container) -> Iterator[Scope]:
    with container.create_scope() as scope:
        yield scope


@pytest.fixture
async def acontainer() -> AsyncIterator[Container]:
    async with Container() as container:
        yield container


@pytest.fixture
async def ascope(acontainer: Container) -> AsyncIterator[Scope]:
    async with acontainer.create_scope() as scope:
        yield scope
