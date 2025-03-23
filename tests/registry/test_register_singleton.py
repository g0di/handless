from typing import Callable

import pytest

from handless import Registry
from handless.descriptor import Singleton
from handless.exceptions import RegistrationError
from tests import helpers


def test_register_singleton_without_factory_registers_a_singleton_factory_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register_singleton(helpers.FakeService)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Singleton(
        helpers.FakeService, enter=True
    )


@helpers.use_factory_callable
def test_register_singleton_registers_a_singleton_factory_service_descriptor(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    ret = sut.register_singleton(helpers.FakeService, factory)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Singleton(factory, enter=True)


@helpers.use_enter
def test_register_singleton_with_options_registers_a_factory_service_descriptor_with_given_options(
    sut: Registry, enter: bool
) -> None:
    ret = sut.register_singleton(helpers.FakeService, enter=enter)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Singleton(
        helpers.FakeService, enter=enter
    )


@helpers.use_invalid_factory_callable
def test_register_singleton_with_untyped_callable_raise_an_error(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register_singleton(helpers.FakeService, factory)
