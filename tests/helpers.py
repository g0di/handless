from typing import NewType, Protocol

import pytest
from typing_extensions import get_args

from handless import Container
from handless.descriptor import Lifetime


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


class FakeServiceWithParams(IFakeService):
    def __init__(self, foo: str, bar: int):
        self.foo = foo
        self.bar = bar


class FakeServiceWithUntypedParams(IFakeService):
    def __init__(self, foo, bar):  # type: ignore[no-untyped-def]
        self.foo = foo
        self.bar = bar


class CallableFakeService(IFakeService):
    def __call__(self) -> FakeService:
        return FakeService()


class CallableFakeServiceWithParams(IFakeService):
    def __call__(self, foo: str, bar: int) -> FakeServiceWithParams:
        return FakeServiceWithParams(foo, bar)


class UntypedCallableFakeService(IFakeService):
    def __call__(self) -> None:
        pass


fake_service_lambda_factory = lambda: FakeService()  # noqa: E731
fake_service_lambda_factory_with_param = lambda c: FakeServiceWithParams(  # noqa: E731
    c.resolve(str), c.resolve(int)
)
fake_service_lambda_factory_with_many_params = lambda a, b, c: FakeService()  # noqa: E731


def fake_service_factory() -> FakeService:
    return FakeService()


def fake_service_factory_with_params(foo: str, bar: int) -> FakeServiceWithParams:
    return FakeServiceWithParams(foo, bar)


def fake_service_factory_with_container_param(
    container: Container,
) -> FakeServiceWithParams:
    return FakeServiceWithParams(container.resolve(str), container.resolve(int))


def fake_service_factory_with_untyped_params(foo, bar) -> FakeServiceWithParams:  # type: ignore[no-untyped-def]
    return FakeServiceWithParams(foo, bar)


use_invalid_factory_callable = pytest.mark.parametrize(
    "factory",
    [
        fake_service_lambda_factory_with_many_params,
        FakeServiceWithUntypedParams,
        fake_service_factory_with_untyped_params,
    ],
)
"""All kind of callables that can not be registered as factory service descriptors."""

use_factory_callable = pytest.mark.parametrize(
    "factory",
    [
        FakeService,
        FakeServiceWithParams,
        fake_service_factory,
        fake_service_factory_with_params,
        fake_service_lambda_factory,
        pytest.param(
            fake_service_lambda_factory_with_param,
            marks=pytest.mark.xfail(reason="Not implemented"),
        ),
        CallableFakeService(),
        CallableFakeServiceWithParams(),
    ],
)
"""All kind of callables that can be registered as factory service descriptor."""

use_factory_function = pytest.mark.parametrize(
    "function",
    [
        fake_service_lambda_factory,
        pytest.param(
            fake_service_lambda_factory_with_param,
            marks=pytest.mark.xfail(reason="Not implemented"),
        ),
        fake_service_factory,
        fake_service_factory_with_params,
    ],
)
"""All kind of functions that can be registered as a factory service descriptor."""

use_invalid_factory_function = pytest.mark.parametrize(
    "function",
    [
        fake_service_lambda_factory_with_many_params,
        fake_service_factory_with_untyped_params,
    ],
)
"""All kind of functions that can not be registered as a factory service descriptor."""

use_lifetimes = pytest.mark.parametrize("lifetime", get_args(Lifetime))
use_enter = pytest.mark.parametrize(
    "enter", [True, False], ids=["Enter CM", "Not enter CM"]
)
