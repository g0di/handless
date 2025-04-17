from collections.abc import Callable

import pytest

from handless import Container, Registry
from tests.helpers import (
    FakeService,
    FakeServiceWithParams,
    fake_service_factory,
    fake_service_factory_with_container_param,
    fake_service_factory_with_params,
    fake_service_lambda_factory,
)


@pytest.mark.parametrize("factory", [fake_service_factory, fake_service_lambda_factory])
def test_resolve_type_calls_binding_factory_and_returns_its_result(
    sut: Container, registry: Registry, factory: Callable[..., FakeService]
) -> None:
    registry.bind(FakeService).to_factory(factory)

    resolved1 = sut.resolve(FakeService)

    assert isinstance(resolved1, FakeService)


@pytest.mark.parametrize(
    "factory",
    [
        pytest.param(fake_service_factory_with_params),
        fake_service_factory_with_container_param,
    ],
)
def test_resolve_type_resolves_its_binding_factory_parameters_before_calling_it(
    sut: Container, registry: Registry, factory: Callable[..., FakeServiceWithParams]
) -> None:
    registry.bind(str).to_value("a")
    registry.bind(int).to_value(42)
    registry.bind(FakeServiceWithParams).to_factory(factory)

    resolved1 = sut.resolve(FakeServiceWithParams)

    assert isinstance(resolved1, FakeServiceWithParams)
    assert resolved1.foo == "a"
    assert resolved1.bar == 42  # noqa: PLR2004


def test_resolve_type_enters_context_manager(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self()

    resolved = sut.resolve(FakeService)

    assert resolved.entered
    assert not resolved.exited


def test_entered_bindings_context_managers_are_exited_on_container_close(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self()

    resolved = sut.resolve(FakeService)

    sut.close()

    assert resolved.exited


def test_resolve_type_not_enter_context_manager_if_enter_is_false(
    sut: Container, registry: Registry
) -> None:
    registry.bind(FakeService).to_self(enter=False)

    resolved = sut.resolve(FakeService)

    assert not resolved.entered
    assert not resolved.exited


def test_resolve_type_not_try_to_enter_non_context_manager_objects(
    sut: Container, registry: Registry
) -> None:
    registry.bind(object).to_self(enter=True)

    try:
        sut.resolve(object)
    except AttributeError as error:
        pytest.fail(reason=str(error))
