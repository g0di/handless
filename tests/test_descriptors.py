from typing import Callable

import pytest
from typing_extensions import Any

from handless import Alias, Factory, Lifetime, Scoped, Singleton, Value
from handless.descriptor import (
    AliasServiceDescriptor,
    Constant,
    FactoryServiceDescriptor,
)
from handless.exceptions import RegistrationError
from tests import helpers
from tests.helpers import (
    use_enter,
    use_lifetimes,
)


class TestValueDescriptor:
    def test_value_factory_returns_a_default_factory_service_descriptor(self) -> None:
        value = object()

        descriptor = Value(value)

        assert descriptor == FactoryServiceDescriptor(
            Constant(value), enter=False, lifetime="singleton"
        )

    @use_enter
    def test_value_factory_returns_a_value_descriptor(self, enter: bool) -> None:
        value = object()

        descriptor = Value(value, enter=enter)

        assert descriptor == FactoryServiceDescriptor(
            Constant(value), enter=enter, lifetime="singleton"
        )


@helpers.use_factory_callable
class TestFactoryDescriptor:
    def test_factory_descriptor_defaults(self, factory: Callable[..., Any]) -> None:
        descriptor = FactoryServiceDescriptor(factory)

        assert descriptor.lifetime == "transient"

    def test_factory_factory_returns_a_default_transient_factory_descriptor(
        self, factory: Callable[..., Any]
    ) -> None:
        descriptor = Factory(factory)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime="transient", enter=True
        )

    @use_lifetimes
    @use_enter
    def test_factory_factory_returns_a_factory_descriptor(
        self, factory: Callable[..., Any], lifetime: Lifetime, enter: bool
    ) -> None:
        descriptor = Factory(factory, lifetime=lifetime, enter=enter)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime=lifetime or "transient", enter=enter
        )

    def test_singleton_factory_returns_a_default_singleton_factory_descriptor(
        self, factory: Callable[..., Any]
    ) -> None:
        descriptor = Singleton(factory)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime="singleton", enter=True
        )

    @use_enter
    def test_singleton_factory_returns_a_singleton_factory_descriptor(
        self, factory: Callable[..., Any], enter: bool
    ) -> None:
        descriptor = Singleton(factory, enter=enter)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime="singleton", enter=enter
        )

    def test_scoped_factory_returns_a_default_scoped_factory_descriptor(
        self, factory: Callable[..., Any]
    ) -> None:
        descriptor = Scoped(factory)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime="scoped", enter=True
        )

    @use_enter
    def test_scoped_factory_returns_a_singleton_factory_descriptor(
        self, factory: Callable[..., Any], enter: bool
    ) -> None:
        descriptor = Scoped(factory, enter=enter)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime="scoped", enter=enter
        )


@helpers.use_invalid_factory_callable
class TestDisallowedFactoryDescriptorCallable:
    def test_factory_descriptor_with_disallowed_callable_raise_an_error(
        self,
        factory: Callable[..., Any],
    ) -> None:
        with pytest.raises(RegistrationError):
            FactoryServiceDescriptor(factory)


class TestAliasDescriptor:
    def test_alias_factory_returns_an_alias_descriptor(self) -> None:
        descriptor = Alias(object)

        assert descriptor == AliasServiceDescriptor(object)
