from typing import NewType, Protocol

import pytest

from handless.lifetimes import Scoped, Singleton, Transient


class IFakeService(Protocol): ...


class FakeService(IFakeService):
    def __init__(self) -> None:
        self.entered = False
        self.reentered = False
        self.exited = False

    def __enter__(self) -> "FakeService":
        if self.entered:
            self.reentered = True
        self.entered = True
        return self

    def __exit__(self, *args: object) -> None:
        self.exited = True


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)

use_lifetimes = pytest.mark.parametrize(
    "lifetime", [Transient(), Scoped(), Singleton()]
)
use_enter = pytest.mark.parametrize(
    "enter", [True, False], ids=["Enter CM", "Not enter CM"]
)
