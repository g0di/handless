from collections.abc import Iterator
from contextlib import contextmanager
from typing import Callable

import pytest

from handless import Lifetime, Registry
from handless._descriptor import ServiceDescriptor
from handless.exceptions import RegistrationError
from tests import helpers


def test_register_factory_without_callable_registers_a_transient_service_descriptor_for_given_type(
    sut: Registry,
) -> None:
    ret = sut.register_factory(helpers.FakeService)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.for_factory(
        helpers.FakeService, enter=True
    )


@helpers.use_factory_callable
def test_register_factory_registers_a_transient_factory_service_descriptor(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    ret = sut.register_factory(helpers.FakeService, factory)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.for_factory(
        factory, enter=True
    )


@helpers.use_lifetimes
@helpers.use_enter
def test_register_factory_with_options_registers_a_factory_service_descriptor_with_given_options(
    sut: Registry, enter: bool, lifetime: Lifetime
) -> None:
    ret = sut.register_factory(helpers.FakeService, lifetime=lifetime, enter=enter)

    assert ret is sut
    assert sut.get(helpers.FakeService) == ServiceDescriptor.for_factory(
        helpers.FakeService, lifetime=lifetime, enter=enter
    )


@helpers.use_invalid_factory_callable
def test_register_factory_with_invalid_callable_raise_an_error(
    sut: Registry, factory: Callable[..., helpers.FakeService]
) -> None:
    with pytest.raises(RegistrationError):
        sut.register_factory(helpers.FakeService, factory)


def test_register_factory_with_generator_function_wraps_it_as_a_context_manager(
    sut: Registry,
) -> None:
    def fake_service_generator(foo: str, bar: int) -> Iterator[helpers.FakeService]:
        yield helpers.FakeService()

    sut.register_factory(helpers.FakeService, fake_service_generator)

    assert sut.get(helpers.FakeService) == ServiceDescriptor.for_factory(
        contextmanager(fake_service_generator)
    )
