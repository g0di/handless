from typing import Callable
from unittest.mock import create_autospec

import pytest

from handless import Registry
from handless.descriptor import (
    AliasServiceDescriptor,
    FactoryServiceDescriptor,
    ServiceDescriptor,
    ValueServiceDescriptor,
)
from handless.exceptions import RegistrationError
from tests.helpers import (
    CallableFakeService,
    FakeService,
    IFakeService,
    use_factory_function,
    use_invalid_factory_function,
)


def test_set_service_descriptor_registers_it_as_is(sut: Registry) -> None:
    descriptor = create_autospec(ServiceDescriptor)
    sut[FakeService] = descriptor

    assert sut.get_descriptor(FakeService) is descriptor


def test_set_type_registers_an_alias_service_descriptor(sut: Registry) -> None:
    sut[IFakeService] = FakeService  # type: ignore[type-abstract]

    assert sut.get_descriptor(IFakeService) == AliasServiceDescriptor(FakeService)


@use_factory_function
def test_set_function_registers_a_transient_factory_service_descriptor(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    sut[FakeService] = function

    assert sut.get_descriptor(FakeService) == FactoryServiceDescriptor(
        function, lifetime="transient", enter=True
    )


@use_invalid_factory_function
def test_set_untyped_function_raises_an_error(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut[FakeService] = function


def test_set_without_value_registers_a_transient_factory_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    sut[FakeService] = ...

    assert sut.get_descriptor(FakeService) == FactoryServiceDescriptor(
        FakeService, lifetime="transient", enter=True
    )


@pytest.mark.parametrize(
    "instance",
    [FakeService(), CallableFakeService()],
    ids=["Object", "Callable object"],
)
def test_set_object_registers_a_value_service_descriptor(
    sut: Registry, instance: IFakeService
) -> None:
    sut[IFakeService] = instance  # type: ignore[type-abstract]

    assert sut.get_descriptor(IFakeService) == ValueServiceDescriptor(
        instance, enter=False
    )
