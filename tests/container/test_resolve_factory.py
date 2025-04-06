from typing import Callable

import pytest

from handless import Registry
from tests.helpers import (
    FakeService,
    FakeServiceWithParams,
    fake_service_factory,
    fake_service_factory_with_container_param,
    fake_service_factory_with_params,
    fake_service_lambda_factory,
    fake_service_lambda_factory_with_param,
)


@pytest.mark.parametrize("factory", [fake_service_factory, fake_service_lambda_factory])
def test_resolve_type_calls_binding_factory_and_returns_its_result(
    factory: Callable[..., FakeService],
) -> None:
    container = Registry().register(FakeService, factory).create_container()

    resolved1 = container.resolve(FakeService)

    assert isinstance(resolved1, FakeService)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(
            fake_service_factory_with_params,
            marks=pytest.mark.xfail(reason="Not possible anymore."),
        ),
        fake_service_factory_with_container_param,
        pytest.param(
            fake_service_lambda_factory_with_param,
            marks=pytest.mark.xfail(reason="Not implemented"),
        ),
    ],
)
def test_resolve_type_resolves_its_binding_factory_parameters_before_calling_it(
    factory: Callable[..., FakeServiceWithParams],
) -> None:
    container = (
        Registry()
        .register(str, "a")
        .register(int, 42)
        .register(FakeServiceWithParams, factory)
        .create_container()
    )

    resolved1 = container.resolve(FakeServiceWithParams)

    assert isinstance(resolved1, FakeServiceWithParams)
    assert resolved1.foo == "a"
    assert resolved1.bar == 42


def test_resolve_type_enters_context_manager() -> None:
    sut = Registry().register(FakeService).create_container()

    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_entered_bindings_context_managers_are_exited_on_container_close() -> None:
    sut = Registry().register(FakeService).create_container()
    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited


def test_resolve_type_not_enter_context_manager_if_enter_is_false() -> None:
    sut = Registry().register(FakeService, enter=False).create_container()

    resolved = sut.resolve(FakeService)

    assert not resolved.entered
    assert not resolved.exited


def test_resolve_type_not_try_to_enter_non_context_manager_objects() -> None:
    sut = Registry().register(object, enter=True).create_container()

    try:
        sut.resolve(object)
    except AttributeError as error:
        pytest.fail(reason=str(error))
