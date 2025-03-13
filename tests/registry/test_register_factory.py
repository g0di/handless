from typing import Callable, Generic, NewType, Protocol, TypedDict, TypeVar

import pytest
from typing_extensions import Unpack

from handless import Factory, Lifetime, Registry
from handless.descriptor import FactoryServiceDescriptor
from tests.registry.test_register_alias import FakeServiceNewType


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


class FakeServiceWithTypedParams(FakeServiceProtocol):
    def __init__(self, foo: object, bar: object) -> None:
        pass


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)


def fake_service_factory() -> FakeService:
    return FakeService()


def fake_service_factory_with_typed_params(
    foo: object, bar: object
) -> FakeServiceWithTypedParams:
    return FakeServiceWithTypedParams(foo, bar)


_T = TypeVar("_T", contravariant=True)


class FactoryOptions(TypedDict, total=False):
    enter: bool
    lifetime: Lifetime


class FactoryRegisterer(Protocol, Generic[_T]):
    def __call__(
        self,
        registry: Registry,
        type_: type[_T],
        factory: Callable[..., _T],
        **options: Unpack[FactoryOptions],
    ) -> None: ...


def register_explicit_factory(
    registry: Registry,
    service_type: type[_T],
    factory: Callable[..., _T],
    **options: Unpack[FactoryOptions],
) -> None:
    registry.register_factory(service_type, factory, **options)


def register_implicit_factory(
    registry: Registry,
    service_type: type[_T],
    factory: Callable[..., _T],
    **options: Unpack[FactoryOptions],
) -> None:
    registry.register(service_type, factory, **options)


def register_factory_descriptor(
    registry: Registry,
    service_type: type[_T],
    factory: Callable[..., _T],
    **options: Unpack[FactoryOptions],
) -> None:
    registry.register(service_type, Factory(factory, **options))


def set_factory(
    registry: Registry,
    service_type: type[_T],
    factory: Callable[..., _T],
) -> None:
    registry[service_type] = factory


def set_factory_descriptor(
    registry: Registry,
    service_type: type[_T],
    factory: Callable[..., _T],
    **options: Unpack[FactoryOptions],
) -> None:
    registry[service_type] = Factory(factory, **options)


@pytest.mark.parametrize(
    "service_type", [FakeServiceProtocol, FakeService, FakeServiceNewType]
)
class TestRegisterFactory:
    """Test that all factory registration methods register the same factoryServiceDescriptor."""

    @pytest.fixture
    def sut(self) -> Registry:
        return Registry()

    @pytest.mark.parametrize(
        "register",
        [
            register_explicit_factory,
            register_factory_descriptor,
            set_factory_descriptor,
        ],
    )
    @pytest.mark.parametrize(
        "factory",
        [
            FakeService,
            lambda: FakeService(),
            lambda c: FakeService(),
            FakeServiceWithTypedParams,
            fake_service_factory,
            fake_service_factory_with_typed_params,
        ],
        ids=[
            "Class constructor",
            "Lambda",
            "Lambda with single param",
            "Class constructor with typed params",
            "Function without parameters",
            "Function with typed parameters",
        ],
    )
    def test_register_explicit_factory_set_a_transient_factory_descriptor_for_this_type(
        self,
        sut: Registry,
        register: FactoryRegisterer[
            FakeServiceProtocol | FakeService | FakeServiceNewType
        ],
        service_type: type[FakeServiceProtocol]
        | type[FakeService]
        | type[FakeServiceNewType],
        factory: type[FakeService] | Callable[..., FakeService],
    ) -> None:
        register(sut, service_type, factory)

        assert sut.get_descriptor(service_type) == FactoryServiceDescriptor(
            factory, enter=True, lifetime="transient"
        )

    @pytest.mark.parametrize(
        "register",
        [register_implicit_factory, set_factory],
    )
    @pytest.mark.parametrize(
        "factory",
        [
            lambda: FakeService(),
            lambda c: FakeService(),
            fake_service_factory,
            fake_service_factory_with_typed_params,
        ],
        ids=[
            "Lambda",
            "Lambda with single param",
            "Function without parameters",
            "Function with typed parameters",
        ],
    )
    def test_register_implicit_callable_set_a_transient_factory_descriptor_for_this_type(
        self,
        sut: Registry,
        register: FactoryRegisterer[
            FakeServiceProtocol | FakeService | FakeServiceNewType
        ],
        service_type: type[FakeServiceProtocol]
        | type[FakeService]
        | type[FakeServiceNewType],
        factory: type[FakeService] | Callable[..., FakeService],
    ) -> None:
        register(sut, service_type, factory)

        assert sut.get_descriptor(service_type) == FactoryServiceDescriptor(
            factory, enter=True, lifetime="transient"
        )
