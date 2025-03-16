from typing import NewType, Protocol, TypedDict

import pytest

from handless import Registry, Value
from handless.descriptor import ValueServiceDescriptor


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)


class ValueDescriptorOptions(TypedDict, total=False):
    enter: bool


use_value_descriptor_options = pytest.mark.parametrize(
    "options",
    [
        ValueDescriptorOptions(),
        ValueDescriptorOptions(enter=True),
        ValueDescriptorOptions(enter=False),
    ],
)


@pytest.fixture
def sut() -> Registry:
    return Registry()


@use_value_descriptor_options
class TestRegisterExplicitValue:
    @pytest.fixture
    def value(self) -> FakeService:
        return FakeService()

    @pytest.fixture
    def expected(
        self, value: FakeService, options: ValueDescriptorOptions
    ) -> ValueServiceDescriptor[FakeService]:
        options.setdefault("enter", False)
        return ValueServiceDescriptor(value, **options)

    def test_register_explicit_value(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register_value(FakeService, value, **options)

        assert ret is sut
        assert sut[FakeService] == expected

    def test_register_explicit_value_for_protocol(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register_value(FakeServiceProtocol, value, **options)

        assert ret is sut
        assert sut[FakeServiceProtocol] == expected

    def test_register_explicit_value_for_new_type(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register_value(FakeServiceNewType, value, **options)

        assert ret is sut
        assert sut[FakeServiceNewType] == expected


@use_value_descriptor_options
class TestRegisterImplicitValue:
    @pytest.fixture
    def value(self) -> FakeService:
        return FakeService()

    @pytest.fixture
    def expected(
        self, value: FakeService, options: ValueDescriptorOptions
    ) -> ValueServiceDescriptor[FakeService]:
        options.setdefault("enter", False)
        return ValueServiceDescriptor(value, **options)

    def test_register_implicit_value(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register(FakeService, value, **options)

        assert ret is sut
        assert sut[FakeService] == expected

    def test_register_implicit_for_protocol(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register(FakeServiceProtocol, value, **options)

        assert ret is sut
        assert sut[FakeServiceProtocol] == expected

    def test_register_implicit_for_new_type(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
        options: ValueDescriptorOptions,
    ) -> None:
        ret = sut.register(FakeServiceNewType, value, **options)

        assert ret is sut
        assert sut[FakeServiceNewType] == expected


@use_value_descriptor_options
class TestRegisterValueDescriptor:
    @pytest.fixture
    def value_descriptor(
        self, options: ValueDescriptorOptions
    ) -> ValueServiceDescriptor[FakeService]:
        return Value(FakeService(), **options)

    def test_register_value_descriptor(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeService, value_descriptor)

        assert ret is sut
        assert sut[FakeService] is value_descriptor

    def test_register_value_descriptor_for_protocol(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceProtocol, value_descriptor)

        assert ret is sut
        assert sut[FakeServiceProtocol] is value_descriptor

    def test_register_value_descriptor_new_type(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceNewType, value_descriptor)

        assert ret is sut
        assert sut[FakeServiceNewType] is value_descriptor


class TestSetValue:
    @pytest.fixture
    def value(self) -> FakeService:
        return FakeService()

    @pytest.fixture
    def expected(self, value: FakeService) -> ValueServiceDescriptor[FakeService]:
        return ValueServiceDescriptor(value)

    def test_set_value(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeService] = value

        assert sut[FakeService] == expected

    def test_set_value_for_protocol(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceProtocol] = value

        assert sut[FakeServiceProtocol] == expected

    def test_set_value_for_new_type(
        self,
        sut: Registry,
        value: FakeService,
        expected: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceNewType] = FakeServiceNewType(value)

        assert sut[FakeServiceNewType] == expected


@use_value_descriptor_options
class TestSetValueDescriptor:
    @pytest.fixture
    def value_descriptor(
        self, options: ValueDescriptorOptions
    ) -> ValueServiceDescriptor[FakeService]:
        return Value(FakeService(), **options)

    def test_set_value_descriptor(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeService] = value_descriptor

        assert sut[FakeService] is value_descriptor

    def test_set_value_descriptor_for_protocol(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceProtocol] = value_descriptor

        assert sut[FakeServiceProtocol] is value_descriptor

    def test_set_value_descriptor_for_new_type(
        self,
        sut: Registry,
        value_descriptor: ValueServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceNewType] = value_descriptor

        assert sut[FakeServiceNewType] is value_descriptor
