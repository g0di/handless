from typing import Callable

import pytest
from typing_extensions import Any

from handless import Alias, Factory, Lifetime, Scoped, Singleton, Value
from handless.descriptor import (
    ServiceDescriptor,
)
from handless.exceptions import RegistrationError
from tests import helpers
from tests.helpers import (
    IFakeService,
    use_enter,
    use_lifetimes,
)


class TestValueDescriptor:
    def test_value_factory_returns_a_default_factory_service_descriptor(self) -> None:
        value = object()

        descriptor = Value(value)

        assert descriptor == ServiceDescriptor(
            factory=lambda: value, enter=False, lifetime="singleton"
        )

    @use_enter
    def test_value_factory_returns_a_value_descriptor(self, enter: bool) -> None:
        value = object()

        descriptor = Value(value, enter=enter)

        assert descriptor == ServiceDescriptor(
            factory=lambda: value, enter=enter, lifetime="singleton"
        )


@helpers.use_factory_callable
class TestFactoryDescriptor:
    def test_factory_descriptor_defaults(
        self, factory: Callable[..., IFakeService]
    ) -> None:
        descriptor = ServiceDescriptor(factory=factory)

        assert descriptor.lifetime == "transient"

    def test_factory_factory_returns_a_default_transient_factory_descriptor(
        self, factory: Callable[..., IFakeService]
    ) -> None:
        descriptor = Factory(factory)

        assert descriptor == ServiceDescriptor(
            factory, lifetime="transient", enter=True
        )

    @use_lifetimes
    @use_enter
    def test_factory_factory_returns_a_factory_descriptor(
        self, factory: Callable[..., IFakeService], lifetime: Lifetime, enter: bool
    ) -> None:
        descriptor = Factory(factory, lifetime=lifetime, enter=enter)

        assert descriptor == ServiceDescriptor(
            factory, lifetime=lifetime or "transient", enter=enter
        )

    def test_singleton_factory_returns_a_default_singleton_factory_descriptor(
        self, factory: Callable[..., IFakeService]
    ) -> None:
        descriptor = Singleton(factory)

        assert descriptor == ServiceDescriptor(
            factory, lifetime="singleton", enter=True
        )

    @use_enter
    def test_singleton_factory_returns_a_singleton_factory_descriptor(
        self, factory: Callable[..., IFakeService], enter: bool
    ) -> None:
        descriptor = Singleton(factory, enter=enter)

        assert descriptor == ServiceDescriptor(
            factory, lifetime="singleton", enter=enter
        )

    def test_scoped_factory_returns_a_default_scoped_factory_descriptor(
        self, factory: Callable[..., IFakeService]
    ) -> None:
        descriptor = Scoped(factory)

        assert descriptor == ServiceDescriptor(factory, lifetime="scoped", enter=True)

    @use_enter
    def test_scoped_factory_returns_a_singleton_factory_descriptor(
        self, factory: Callable[..., IFakeService], enter: bool
    ) -> None:
        descriptor = Scoped(factory, enter=enter)

        assert descriptor == ServiceDescriptor(factory, lifetime="scoped", enter=enter)


@helpers.use_invalid_factory_callable
class TestDisallowedFactoryDescriptorCallable:
    def test_factory_descriptor_with_disallowed_callable_raise_an_error(
        self,
        factory: Callable[..., Any],
    ) -> None:
        with pytest.raises(RegistrationError):
            ServiceDescriptor(factory)


class TestAliasDescriptor:
    def test_alias_factory_returns_an_alias_descriptor(self) -> None:
        descriptor = Alias(object)

        assert descriptor == ServiceDescriptor(implementation=object)
