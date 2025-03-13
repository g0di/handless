from typing import Generic, NewType, Protocol, TypedDict, TypeVar

import pytest
from typing_extensions import Unpack

from handless import Registry, Value
from handless.descriptor import ValueServiceDescriptor
from tests.test_descriptors import use_enter


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)


class ValueDescriptorOptions(TypedDict, total=False):
    enter: bool


_T = TypeVar("_T", contravariant=True)


class ValueRegisterer(Protocol, Generic[_T]):
    def __call__(
        self,
        registry: Registry,
        type_: type[_T],
        value: _T,
        **kwargs: Unpack[ValueDescriptorOptions],
    ) -> None: ...


def register_explicit_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueDescriptorOptions],
) -> None:
    registry.register_value(service_type, value, **kwargs)


def register_implicit_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueDescriptorOptions],
) -> None:
    registry.register(service_type, value)


def register_implicit_value_descriptor(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueDescriptorOptions],
) -> None:
    registry.register(service_type, Value(value, **kwargs))


def set_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueDescriptorOptions],
) -> None:
    registry[service_type] = value


def set_value_descriptor(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueDescriptorOptions],
) -> None:
    registry[service_type] = Value(value, **kwargs)


@pytest.mark.parametrize(
    "service_type", [FakeServiceProtocol, FakeService, FakeServiceNewType]
)
class TestRegisterValue:
    """Test that all value registration methods register the same ValueServiceDescriptor."""

    @pytest.fixture
    def sut(self) -> Registry:
        return Registry()

    @pytest.mark.parametrize(
        "register",
        [
            register_explicit_value,
            register_implicit_value,
            register_implicit_value_descriptor,
            set_value,
            set_value_descriptor,
        ],
    )
    def test_register_value_set_a_value_descriptor_for_this_type(
        self,
        sut: Registry,
        register: ValueRegisterer[
            FakeServiceProtocol | FakeService | FakeServiceNewType
        ],
        service_type: type[FakeServiceProtocol]
        | type[FakeService]
        | type[FakeServiceNewType],
    ) -> None:
        value = FakeService()

        register(sut, service_type, value)

        assert sut.get_descriptor(service_type) == ValueServiceDescriptor(
            value, enter=False
        )

    @pytest.mark.parametrize(
        "register",
        [
            register_explicit_value,
            register_implicit_value_descriptor,
            set_value_descriptor,
        ],
    )
    @use_enter
    def test_register_value_with_options_set_a_value_descriptor_for_this_type_with_given_options(
        self,
        sut: Registry,
        register: ValueRegisterer[
            FakeServiceProtocol | FakeService | FakeServiceNewType
        ],
        service_type: type[FakeServiceProtocol]
        | type[FakeService]
        | type[FakeServiceNewType],
        enter: bool,
    ) -> None:
        value = FakeService()

        register(sut, service_type, value, enter=enter)

        assert sut.get_descriptor(service_type) == ValueServiceDescriptor(
            value, enter=enter
        )

    # def test_register_value_type_hints(self, sut: Registry) -> None:
    #     sut.register_value(FakeServiceProtocol, object())
    #     sut.register_value(FakeService, 42)
    #     sut.register_value(FakeServiceNewType, FakeService())
