from typing import cast

import pytest

from handless import Registry


@pytest.fixture
def sut(request: pytest.FixtureRequest) -> Registry:
    registry_options_mark = cast(
        "pytest.Mark | None", request.node.get_closest_marker("registry_options")
    )
    registry_options = (
        registry_options_mark.kwargs if registry_options_mark is not None else {}
    )
    return Registry(**registry_options)
