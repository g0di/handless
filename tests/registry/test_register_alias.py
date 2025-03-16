from typing import NewType, Protocol

import pytest

from handless import Alias, Registry
from handless.container import AliasServiceDescriptor


class FakeServiceProtocol(Protocol): ...


class FakeService(FakeServiceProtocol):
    pass


FakeServiceNewType = NewType("FakeServiceNewType", FakeService)


@pytest.fixture
def sut() -> Registry:
    return Registry()


class TestRegisterExplicitAlias:
    @pytest.fixture
    def alias(self) -> type[FakeService]:
        return FakeService

    @pytest.fixture
    def expected(self, alias: type[FakeService]) -> AliasServiceDescriptor[FakeService]:
        return AliasServiceDescriptor(alias)

    def test_register_explicit_alias(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register_alias(FakeService, alias)

        assert ret is sut
        assert sut[FakeService] == expected

    def test_register_explicit_alias_for_protocol(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register_alias(FakeServiceProtocol, alias)

        assert ret is sut
        assert sut[FakeServiceProtocol] == expected

    def test_register_explicit_alias_for_new_type(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register_alias(FakeServiceNewType, alias)

        assert ret is sut
        assert sut[FakeServiceNewType] == expected


class TestRegisterImplicitAlias:
    @pytest.fixture
    def alias(self) -> type[FakeService]:
        return FakeService

    @pytest.fixture
    def expected(self, alias: type[FakeService]) -> AliasServiceDescriptor[FakeService]:
        return AliasServiceDescriptor(alias)

    def test_register_implicit_alias(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeService, alias)

        assert ret is sut
        assert sut[FakeService] == expected

    def test_register_implicit_for_protocol(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceProtocol, alias)

        assert ret is sut
        assert sut[FakeServiceProtocol] == expected

    def test_register_implicit_for_new_type(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceNewType, alias)

        assert ret is sut
        assert sut[FakeServiceNewType] == expected


class TestRegisterAliasDescriptor:
    @pytest.fixture
    def alias_descriptor(self) -> AliasServiceDescriptor[FakeService]:
        return Alias(FakeService)

    def test_register_alias_descriptor(
        self,
        sut: Registry,
        alias_descriptor: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeService, alias_descriptor)

        assert ret is sut
        assert sut[FakeService] is alias_descriptor

    def test_register_alias_descriptor_for_protocol(
        self,
        sut: Registry,
        alias_descriptor: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceProtocol, alias_descriptor)

        assert ret is sut
        assert sut[FakeServiceProtocol] is alias_descriptor

    def test_register_alias_descriptor_new_type(
        self,
        sut: Registry,
        alias_descriptor: AliasServiceDescriptor[FakeService],
    ) -> None:
        ret = sut.register(FakeServiceNewType, alias_descriptor)

        assert ret is sut
        assert sut[FakeServiceNewType] is alias_descriptor


class TestSetAlias:
    @pytest.fixture
    def alias(self) -> type[FakeService]:
        return FakeService

    @pytest.fixture
    def expected(self, alias: type[FakeService]) -> AliasServiceDescriptor[FakeService]:
        return AliasServiceDescriptor(alias)

    def test_set_alias(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeService] = alias

        assert sut[FakeService] == expected

    def test_set_alias_for_protocol(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceProtocol] = alias

        assert sut[FakeServiceProtocol] == expected

    def test_set_alias_for_new_type(
        self,
        sut: Registry,
        alias: type[FakeService],
        expected: AliasServiceDescriptor[FakeService],
    ) -> None:
        sut[FakeServiceNewType] = FakeServiceNewType(alias)

        assert sut[FakeServiceNewType] == expected


class TestSetAliasDescriptor:
    @pytest.fixture
    def alias_descriptor(self) -> AliasServiceDescriptor[FakeService]:
        return Alias(FakeService)

    def test_set_alias_descriptor(
        self, sut: Registry, alias_descriptor: type[FakeService]
    ) -> None:
        sut[FakeService] = alias_descriptor

        assert sut[FakeService] is alias_descriptor

    def test_set_alias_descriptor_for_protocol(
        self, sut: Registry, alias_descriptor: type[FakeService]
    ) -> None:
        sut[FakeServiceProtocol] = alias_descriptor

        assert sut[FakeServiceProtocol] is alias_descriptor

    def test_set_alias_descriptor_for_new_type(
        self, sut: Registry, alias_descriptor: type[FakeService]
    ) -> None:
        sut[FakeServiceNewType] = FakeServiceNewType(alias_descriptor)

        assert sut[FakeServiceNewType] is alias_descriptor
