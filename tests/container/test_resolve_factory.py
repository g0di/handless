from typing import Callable

import pytest

from handless import Registry
from tests.helpers import (
    CallableFakeService,
    CallableFakeServiceWithParams,
    FakeService,
    FakeServiceWithParams,
    fake_service_factory,
    fake_service_factory_with_container_param,
    fake_service_factory_with_params,
    fake_service_lambda_factory,
    fake_service_lambda_factory_with_param,
)


@pytest.mark.parametrize(
    "factory",
    [
        FakeService,
        fake_service_factory,
        fake_service_lambda_factory,
        CallableFakeService(),
    ],
)
def test_resolve_a_factory_descriptor_calls_given_callable_and_returns_its_result(
    factory: Callable[..., FakeService],
) -> None:
    container = Registry().register_factory(FakeService, factory).create_container()

    resolved1 = container.resolve(FakeService)

    assert isinstance(resolved1, FakeService)


@pytest.mark.parametrize(
    "factory",
    [
        FakeServiceWithParams,
        fake_service_factory_with_params,
        fake_service_factory_with_container_param,
        CallableFakeServiceWithParams(),
        fake_service_lambda_factory_with_param,
    ],
)
def test_resolve_a_factory_descriptor_resolves_its_parameters_before_calling_it(
    factory: Callable[..., FakeServiceWithParams],
) -> None:
    container = (
        Registry()
        .register_value(str, "a")
        .register_value(int, 42)
        .register_factory(FakeServiceWithParams, factory)
        .create_container()
    )

    resolved1 = container.resolve(FakeServiceWithParams)

    assert isinstance(resolved1, FakeServiceWithParams)
    assert resolved1.foo == "a"
    assert resolved1.bar == 42


def test_resolve_factory_enter_context_manager_if_one_is_returned() -> None:
    sut = Registry().register_factory(FakeService).create_container()

    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_resolve_factory_not_enter_context_manager_if_one_is_returned_but_enter_is_false() -> (
    None
):
    sut = Registry().register_factory(FakeService, enter=False).create_container()

    resolved = sut.resolve(FakeService)

    assert not resolved.entered
    assert not resolved.exited
