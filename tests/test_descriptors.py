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
    use_factories,
    use_lifetimes,
)


def test_value_descriptor_factory_returns_a_value_descriptor() -> None:
    value = object()

    descriptor = Value(value)

    assert descriptor == ValueServiceDescriptor(value)


@use_factories
@use_lifetimes
def test_factory_descriptor_factory_returns_a_factory_descriptor(
    factory: ServiceFactory[Any], lifetime: Lifetime | None
) -> None:
    descriptor = Factory(factory, lifetime=lifetime)

    assert descriptor == FactoryServiceDescriptor(
        factory, lifetime=lifetime or "transient"
    )


@use_factories
def test_singleton_descriptor_factory_returns_a_singleton_descriptor(
    factory: ServiceFactory[Any],
) -> None:
    descriptor = Singleton(factory)

    assert descriptor == FactoryServiceDescriptor(factory, lifetime="singleton")


@use_factories
def test_scoped_descriptor_factory_returns_a_scoped_descriptor(
    factory: ServiceFactory[Any],
) -> None:
    descriptor = Scoped(factory)

    assert descriptor == FactoryServiceDescriptor(factory, lifetime="scoped")


def test_alias_descriptor_factory_returns_a_descriptor_alias() -> None:
    descriptor = Alias(FakeService)

    assert descriptor == AliasServiceDescriptor(FakeService)


def untyped_func(foo: str, bar): ...


class UntypedClass:
    def __init__(self, foo, bar: str):
        pass


@pytest.mark.parametrize("factory", [untyped_func, UntypedClass])
def test_create_factory_descriptor_with_callable_missing_params_type_annotations_raise_an_error(
    factory: Callable[..., Any],
) -> None:
    with pytest.raises(RegistrationError):
        FactoryServiceDescriptor(factory)


def test_create_factory_descriptor_with_lambda_without_parameters() -> None:
    try:
        FactoryServiceDescriptor(lambda: "")
    except Exception:
        pytest.fail("Expected no error to be raised")


def test_create_factory_descriptor_with_lambda_with_a_single_parameter() -> None:
    try:
        FactoryServiceDescriptor(lambda c: "")
    except Exception:
        pytest.fail("Expected no error to be raised")


def test_create_factory_descriptor_with_lambda_having_more_than_1_arg_raises_an_error() -> (
    None
):
    with pytest.raises(RegistrationError):
        FactoryServiceDescriptor(lambda a, b, c: "")
