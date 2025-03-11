from typing import Protocol

import pytest
from typing_extensions import get_args

from handless.descriptor import Lifetime


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


class FakeServiceImpl(FakeService):
    pass


def fake_service_factory() -> FakeService:
    return FakeService()


class FakeServiceFactory:
    def __call__(self) -> FakeService:
        return FakeService()


def untyped_func(foo: str, bar): ...  # type: ignore[no-untyped-def]


class UntypedClass:
    def __init__(self, foo, bar: str):  # type: ignore[no-untyped-def]
        pass


use_factories = pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda: FakeService(), id="Lambda function without params"),
        pytest.param(lambda c: FakeService(), id="Lambda function with single param"),
        pytest.param(FakeService, id="Class constructor"),
        pytest.param(fake_service_factory, id="Regular function"),
        pytest.param(FakeServiceFactory(), id="Callable class instance"),
    ],
)
use_disallowed_factories = pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            lambda a, b: FakeService(), id="Lambda function with more than 1 parameter"
        ),
        pytest.param(UntypedClass, id="Untyped class constructor"),
        pytest.param(untyped_func, id="Untyped regular function"),
    ],
)
use_lifetimes = pytest.mark.parametrize("lifetime", get_args(Lifetime))
use_enter = pytest.mark.parametrize(
    "enter", [True, False], ids=["Enter CM", "Not enter CM"]
)
