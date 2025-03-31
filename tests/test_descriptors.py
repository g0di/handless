from inspect import Parameter
from typing import Callable

import pytest
from typing_extensions import Any

from handless import Lifetime, ServiceDescriptor
from handless.exceptions import RegistrationError
from tests import helpers


class TestValueServiceDescriptor:
    def test_value_returns_a_singleton_service_descriptor(self) -> None:
        value = object()

        descriptor = ServiceDescriptor.value(value)

        assert descriptor == ServiceDescriptor(
            getter=lambda: value, enter=False, lifetime="singleton"
        )

    @helpers.use_enter
    def test_value_with_options_returns_a_singleton_service_descriptor(
        self, enter: bool
    ) -> None:
        value = object()

        descriptor = ServiceDescriptor.value(value, enter=enter)

        assert descriptor == ServiceDescriptor(
            getter=lambda: value, enter=enter, lifetime="singleton"
        )


@helpers.use_factory_callable
class TestFactoryServiceDescriptor:
    def test_service_descriptor_is_transient_by_default(
        self, factory: Callable[..., helpers.IFakeService]
    ) -> None:
        descriptor = ServiceDescriptor(getter=factory)

        assert descriptor.lifetime == "transient"

    def test_factory_returns_a_transient_service_descriptor(
        self, factory: Callable[..., helpers.IFakeService]
    ) -> None:
        descriptor = ServiceDescriptor.factory(factory)

        assert descriptor == ServiceDescriptor(
            factory, lifetime="transient", enter=True
        )

    @helpers.use_lifetimes
    @helpers.use_enter
    def test_factory_with_options_returns_a_transient_service_descriptor(
        self,
        factory: Callable[..., helpers.IFakeService],
        lifetime: Lifetime,
        enter: bool,
    ) -> None:
        descriptor = ServiceDescriptor.factory(factory, lifetime=lifetime, enter=enter)

        assert descriptor == ServiceDescriptor(factory, lifetime=lifetime, enter=enter)


@helpers.use_invalid_factory_callable
def test_service_descriptor_with_invalid_callable_raises_an_error(
    factory: Callable[..., Any],
) -> None:
    with pytest.raises(RegistrationError):
        ServiceDescriptor(factory)


class TestImplementationDescriptor:
    def test_implementation_returns_a_transient_service_descriptor(self) -> None:
        descriptor = ServiceDescriptor.implementation(object)

        assert descriptor == ServiceDescriptor(
            lambda x: x,
            lifetime="transient",
            enter=False,
            params={
                "x": Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=object)
            },
        )
