from typing import TypedDict

import pytest

from handless import LifetimeLiteral, Registry
from tests.helpers import FakeService


class SelfOptions(TypedDict, total=False):
    enter: bool
    lifetime: LifetimeLiteral


@pytest.mark.parametrize(
    "options",
    [
        SelfOptions(),
        SelfOptions(enter=True, lifetime="singleton"),
        SelfOptions(enter=False, lifetime="scoped"),
    ],
)
def test_register_self_is_same_as_registering_factory_with_given_type(
    options: SelfOptions,
) -> None:
    registry1 = Registry()
    registry2 = Registry()

    registry1.bind(FakeService).to_self(**options)
    registry2.bind(FakeService).to_factory(FakeService, **options)

    assert registry1.lookup(FakeService) == registry2.lookup(FakeService)
