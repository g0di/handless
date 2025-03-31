from typing import Callable

import pytest

from handless import Registry, ServiceDescriptor
from handless.exceptions import RegistrationError
from tests import helpers


def test_register_singleton_without_factory_registers_a_singleton_factory_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register_singleton(helpers.FakeService)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        helpers.FakeService, enter=True, lifetime="singleton"
    )


def test_register_singleton_with_value_registers_a_singleton_service_descriptor_returning_this_value(
    sut: Registry,
) -> None:
    value = helpers.FakeService()
    ret = sut.register_singleton(helpers.FakeService, value)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.value(value)


@helpers.use_enter
def test_register_singleton_with_value_and_options_registers_a_singleton_service_descriptor_with_given_options_returning_this_value(
    sut: Registry, enter: bool
) -> None:
    value = helpers.FakeService()
    ret = sut.register_singleton(helpers.FakeService, value, enter=enter)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.value(value, enter=enter)


@helpers.use_factory_callable
def test_register_singleton_registers_a_singleton_factory_service_descriptor(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    ret = sut.register_singleton(helpers.FakeService, factory)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        factory, enter=True, lifetime="singleton"
    )


@helpers.use_enter
def test_register_singleton_with_options_registers_a_factory_service_descriptor_with_given_options(
    sut: Registry, enter: bool
) -> None:
    ret = sut.register_singleton(helpers.FakeService, enter=enter)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        helpers.FakeService, enter=enter, lifetime="singleton"
    )


@helpers.use_invalid_factory_callable
def test_register_singleton_with_invalid_callable_raises_an_error(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register_singleton(helpers.FakeService, factory)
