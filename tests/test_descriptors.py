from typing import Callable

import pytest
from typing_extensions import Any

from handless import Alias, Factory, Lifetime, Scoped, Singleton, Value
from handless.descriptor import (
    AliasServiceDescriptor,
    FactoryServiceDescriptor,
    RegistrationError,
    ServiceFactory,
    ValueServiceDescriptor,
)
from tests.helpers import (
    FakeService,
    UntypedClass,
    untyped_func,
    use_factories,
    use_lifetimes,
)


def test_value_shortcut_returns_a_value_descriptor() -> None:
    value = object()

    descriptor = Value(value)

    assert descriptor == ValueServiceDescriptor(value)


@use_factories
@use_lifetimes
def test_factory_shortcut_returns_a_factory_descriptor(
    factory: ServiceFactory[Any], lifetime: Lifetime | None
) -> None:
    descriptor = Factory(factory, lifetime=lifetime)

    assert descriptor == FactoryServiceDescriptor(
        factory, lifetime=lifetime or "transient"
    )


@use_factories
def test_singleton_shortcut_returns_a_singleton_descriptor(
    factory: ServiceFactory[Any],
) -> None:
    descriptor = Singleton(factory)

    assert descriptor == FactoryServiceDescriptor(factory, "singleton")


@use_factories
def test_scoped_shortcut_returns_a_scoped_descriptor(
    factory: ServiceFactory[Any],
) -> None:
    descriptor = Scoped(factory)

    assert descriptor == FactoryServiceDescriptor(factory, "scoped")


def test_alias_shortcut_returns_a_descriptor_alias() -> None:
    descriptor = Alias(FakeService)

    assert descriptor == AliasServiceDescriptor(FakeService)


@pytest.mark.parametrize("factory", [untyped_func, UntypedClass])
def test_factory_with_missing_type_annotations_raise_an_error(
    factory: Callable[..., Any],
) -> None:
    with pytest.raises(RegistrationError):
        FactoryServiceDescriptor(factory)


def test_factory_with_lambda_having_more_than_1_arg_raises_an_error() -> None:
    with pytest.raises(RegistrationError):
        FactoryServiceDescriptor(lambda a, b, c: "")
