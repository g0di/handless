import pytest
from typing_extensions import get_args

from handless.descriptor import Lifetime


class FakeService:
    pass


class FakeServiceImpl(FakeService):
    pass


def fake_service_factory() -> FakeService:
    return FakeService()


class FakeServiceFactory:
    def __call__(self) -> FakeService:
        return FakeService()


use_factories = pytest.mark.parametrize(
    "factory",
    [
        pytest.param(lambda: FakeService(), id="Lambda function"),
        pytest.param(FakeService, id="Class constructor"),
        pytest.param(fake_service_factory, id="Regular function"),
        pytest.param(FakeServiceFactory(), id="Callable class instance"),
    ],
)
use_lifetimes = pytest.mark.parametrize("lifetime", [None, *get_args(Lifetime)])
use_enter = pytest.mark.parametrize("enter", [True, False])
