from typing import Callable

import pytest

from handless import Registry
from handless._descriptor import ServiceDescriptor
from handless.exceptions import RegistrationError
from tests import helpers


def test_register_scoped_without_factory_registers_a_scoped_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register_scoped(helpers.FakeService)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        helpers.FakeService, enter=True, lifetime="scoped"
    )


@helpers.use_factory_callable
def test_register_scoped_registers_a_scoped_service_descriptor_for_given_callable(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    ret = sut.register_scoped(helpers.FakeService, factory)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        factory, enter=True, lifetime="scoped"
    )


@helpers.use_enter
def test_register_scoped_with_options_registers_a_scoped_service_descriptor_with_given_options(
    sut: Registry, enter: bool
) -> None:
    ret = sut.register_scoped(helpers.FakeService, enter=enter)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.factory(
        helpers.FakeService, enter=enter, lifetime="scoped"
    )


@helpers.use_invalid_factory_callable
def test_register_scoped_with_invalid_callable_raises_an_error(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register_scoped(helpers.FakeService, factory)
