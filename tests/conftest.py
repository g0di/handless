from collections.abc import Iterator
from typing import cast

import pytest

from handless import Container, Registry, Scope


@pytest.fixture
def registry(request: pytest.FixtureRequest) -> Registry:
    registry_options_mark = cast(
        "pytest.Mark | None", request.node.get_closest_marker("registry_options")
    )
    registry_options = (
        registry_options_mark.kwargs if registry_options_mark is not None else {}
    )
    return Registry(**registry_options)


@pytest.fixture
def sut(registry: Registry) -> Iterator[Container]:
    with Container(registry) as container:
        yield container


@pytest.fixture
def scope(sut: Container) -> Iterator[Scope]:
    with sut.create_scope() as scope:
        yield scope
