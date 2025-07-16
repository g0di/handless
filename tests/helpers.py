from typing import Any, NewType, Protocol

import pytest

from handless.lifetimes import Contextual, Singleton, Transient


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


def create_fake_service() -> FakeService:
    return FakeService()


class FakeServiceWithParams(IFakeService):
    def __init__(self, foo: str, bar: int) -> None:
        pass


class FakeServiceWithOneParam(IFakeService):
    def __init__(self, foo: str) -> None:
        pass


class FakeServiceWithUntypedParams(IFakeService):
    def __init__(self, foo, bar) -> None:  # type: ignore  # noqa: ANN001, PGH003
        pass


def create_fake_service_with_params(
    foo: str,
    *args: Any,  # noqa: ANN401, ARG001
    bar: int = 5,
    **kwargs: Any,  # noqa: ANN401, ARG001
) -> FakeServiceWithParams:
    return FakeServiceWithParams(foo, bar)


def create_fake_service_with_untyped_params(  # type: ignore  # noqa: PGH003
    foo,  # noqa: ANN001
    bar,  # noqa: ANN001
) -> FakeServiceWithParams:
    return FakeServiceWithParams(foo, bar)


FakeServiceNewType = NewType("FakeServiceNewType", IFakeService)  # type: ignore[misc]

use_lifetimes = pytest.mark.parametrize(
    "lifetime", [Transient(), Contextual(), Singleton()]
)
use_enter = pytest.mark.parametrize(
    "enter", [True, False], ids=["Enter CM", "Not enter CM"]
)
