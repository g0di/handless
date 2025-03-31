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
def test_resolve_service_descriptor_calls_given_callable_and_returns_its_result(
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
        pytest.param(
            fake_service_lambda_factory_with_param,
            marks=pytest.mark.xfail(reason="Not implemented"),
        ),
    ],
)
def test_resolve_service_descriptor_resolves_its_parameters_before_calling_it(
    factory: Callable[..., FakeServiceWithParams],
) -> None:
    container = (
        Registry()
        .register_singleton(str, "a")
        .register_singleton(int, 42)
        .register_factory(FakeServiceWithParams, factory)
        .create_container()
    )

    resolved1 = container.resolve(FakeServiceWithParams)

    assert isinstance(resolved1, FakeServiceWithParams)
    assert resolved1.foo == "a"
    assert resolved1.bar == 42


def test_resolve_service_descriptor_enters_context_manager_if_one_is_returned() -> None:
    sut = Registry().register_factory(FakeService).create_container()

    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_service_descriptor_returned_context_manager_is_exited_on_container_close() -> (
    None
):
    sut = Registry().register_factory(FakeService).create_container()
    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited


def test_resolve_factory_not_enter_context_manager_if_one_is_returned_but_enter_is_false() -> (
    None
):
    sut = Registry().register_factory(FakeService, enter=False).create_container()

    resolved = sut.resolve(FakeService)

    assert not resolved.entered
    assert not resolved.exited


def test_resolve_service_descriptor_not_enter_non_context_manager_returned_object() -> (
    None
):
    sut = Registry().register_factory(object, enter=True).create_container()

    try:
        sut.resolve(object)
    except AttributeError as error:
        pytest.fail(reason=str(error))
