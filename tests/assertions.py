from typing_extensions import Any

from handless.descriptor import (
    AliasServiceDescriptor,
    Factory,
    FactoryServiceDescriptor,
    Lifetime,
    ServiceDescriptor,
    ValueServiceDescriptor,
)
from handless.registry import Registry


def assert_has_descriptor(
    registry: Registry, service_type: type, descriptor: ServiceDescriptor
):
    assert registry.get_descriptor(service_type) is descriptor


def assert_has_factory_descriptor(
    registry: Registry,
    service_type: type,
    factory: Factory[Any],
    *,
    lifetime: Lifetime | None = None,
):
    assert registry.get_descriptor(service_type) == FactoryServiceDescriptor(
        factory, lifetime=lifetime or "transient"
    )


def assert_has_singleton_descriptor(
    registry: Registry, service_type: type, factory: Factory[Any]
):
    assert_has_factory_descriptor(registry, service_type, factory, lifetime="singleton")


def assert_has_scoped_descriptor(
    registry: Registry, service_type: type, factory: Factory[Any]
):
    assert_has_factory_descriptor(registry, service_type, factory, lifetime="scoped")


def assert_has_value_descriptor(registry: Registry, service_type: type, value: Any):
    assert registry.get_descriptor(service_type) == ValueServiceDescriptor(value)


def assert_has_alias_descriptor(registry: Registry, service_type: type, impl: Any):
    assert registry.get_descriptor(service_type) == AliasServiceDescriptor(impl)
