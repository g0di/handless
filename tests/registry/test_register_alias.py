from types import EllipsisType
from typing import Generic, NewType, Protocol, TypeVar

import pytest

from handless import Alias, Registry
from handless.container import AliasServiceDescriptor


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)


_T = TypeVar("_T", contravariant=True)


class AliasRegisterer(Protocol, Generic[_T]):
    def __call__(
        self,
        registry: Registry,
        type_: type[_T],
        alias: type[_T],
    ) -> None: ...


def register_explicit_alias(
    registry: Registry,
    service_type: type[_T],
    alias: type[_T],
) -> None:
    registry.register_alias(service_type, alias)


def register_implicit_alias(
    registry: Registry,
    service_type: type[_T],
    alias: type[_T],
) -> None:
    registry.register(service_type, alias)


def register_implicit_alias_descriptor(
    registry: Registry,
    service_type: type[_T],
    alias: type[_T],
) -> None:
    registry.register(service_type, Alias(alias))


def set_alias(
    registry: Registry,
    service_type: type[_T],
    alias: type[_T] | EllipsisType,
) -> None:
    registry[service_type] = alias


def set_alias_descriptor(
    registry: Registry,
    service_type: type[_T],
    alias: type[_T],
) -> None:
    registry[service_type] = Alias(alias)


class TestRegisterValue:
    """Test that all alias registration methods register the same AliasServiceDescriptor."""

    @pytest.fixture
    def sut(self) -> Registry:
        return Registry()

    @pytest.mark.parametrize(
        "register",
        [
            register_explicit_alias,
            register_implicit_alias,
            register_implicit_alias_descriptor,
            set_alias,
            set_alias_descriptor,
        ],
    )
    @pytest.mark.parametrize("service_type", [FakeServiceProtocol, FakeService])
    def test_register_alias_set_an_alias_descriptor_for_this_type(
        self,
        sut: Registry,
        register: AliasRegisterer[FakeServiceProtocol | FakeService],
        service_type: type[FakeServiceProtocol]
        | type[FakeService]
        | type[FakeServiceNewType],
    ) -> None:
        register(sut, service_type, FakeService)

        assert sut.get_descriptor(service_type) == AliasServiceDescriptor(FakeService)
