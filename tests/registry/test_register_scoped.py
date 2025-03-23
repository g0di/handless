from typing import Callable

import pytest

from handless import Registry
from handless.descriptor import Scoped
from handless.exceptions import RegistrationError
from tests import helpers


def test_register_scoped_without_factory_registers_a_scoped_factory_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register_scoped(helpers.FakeService)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Scoped(
        helpers.FakeService, enter=True
    )


@helpers.use_factory_callable
def test_register_scoped_registers_a_scoped_factory_service_descriptor(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    ret = sut.register_scoped(helpers.FakeService, factory)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Scoped(factory, enter=True)


@helpers.use_enter
def test_register_scoped_with_options_registers_a_factory_service_descriptor_with_given_options(
    sut: Registry, enter: bool
) -> None:
    ret = sut.register_scoped(helpers.FakeService, enter=enter)

    assert ret is sut
    assert sut.get_descriptor(helpers.FakeService) == Scoped(
        helpers.FakeService, enter=enter
    )


@helpers.use_invalid_factory_callable
def test_register_scoped_with_untyped_callable_raise_an_error(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register_scoped(helpers.FakeService, factory)
