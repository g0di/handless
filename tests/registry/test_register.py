from typing import Callable
from unittest.mock import create_autospec

import pytest

from handless import Alias, Factory, Lifetime, Registry
from handless.descriptor import (
    ServiceDescriptor,
    Value,
)
from handless.exceptions import RegistrationError
from tests.helpers import (
    CallableFakeService,
    FakeService,
    IFakeService,
    use_enter,
    use_factory_function,
    use_invalid_factory_function,
    use_lifetimes,
)


def test_register_service_descriptor_registers_it_as_is(sut: Registry) -> None:
    descriptor = create_autospec(ServiceDescriptor)
    ret = sut.register(FakeService, descriptor)

    assert ret is sut
    assert sut.get_descriptor(FakeService) is descriptor


def test_register_type_registers_an_alias_service_descriptor(sut: Registry) -> None:
    ret = sut.register(IFakeService, FakeService)  # type: ignore[type-abstract]

    assert ret is sut
    assert sut.get_descriptor(IFakeService) == Alias(FakeService)


@use_factory_function
def test_register_function_registers_a_transient_factory_service_descriptor(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    ret = sut.register(FakeService, function)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == Factory(function)


@use_invalid_factory_function
def test_set_untyped_function_raises_an_error(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register(FakeService, function)


def test_register_without_value_registers_a_transient_factory_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register(FakeService)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == Factory(FakeService)


@use_lifetimes
@use_enter
def test_register_without_value_and_with_options_registers_a_factory_service_descriptor_for_given_type_and_options(
    sut: Registry, enter: bool, lifetime: Lifetime
) -> None:
    ret = sut.register(FakeService, enter=enter, lifetime=lifetime)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == Factory(
        FakeService, lifetime=lifetime, enter=enter
    )


@pytest.mark.parametrize(
    "instance",
    [FakeService(), CallableFakeService()],
    ids=["Object", "Callable object"],
)
def test_register_object_registers_a_value_service_descriptor(
    sut: Registry, instance: IFakeService
) -> None:
    ret = sut.register(FakeService, instance)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == Value(instance, enter=False)


@use_enter
def test_register_object_with_options_registers_a_value_service_descriptor_with_given_options(
    sut: Registry, enter: bool
) -> None:
    instance = FakeService()
    ret = sut.register(FakeService, instance, enter=enter)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == Value(instance, enter=enter)
