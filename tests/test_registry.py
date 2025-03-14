from operator import setitem

import pytest
from typing_extensions import Any

from handless import Lifetime, Registry, Value
from handless.container import ValueServiceDescriptor
from handless.descriptor import (
    FactoryServiceDescriptor,
    ServiceFactory,
)
from handless.exceptions import RegistrationError
from tests.assertions import (
    assert_has_alias_descriptor,
    assert_has_descriptor,
    assert_has_factory_descriptor,
    assert_has_scoped_descriptor,
    assert_has_singleton_descriptor,
    assert_has_value_descriptor,
)
from tests.helpers import (
    FakeService,
    FakeServiceImpl,
    fake_service_factory,
    use_factories,
    use_lifetimes,
)
from tests.test_descriptors import use_enter


class TestRegisterValue:
    @pytest.mark.parametrize(
        "register",
        [
            lambda r, v: r.register_value(FakeService, v),
            lambda r, v: r.register(FakeService, v),
            lambda r, v: r.register(FakeService, Value(v)),
            lambda r, v: setitem(r, FakeService, v),
            lambda r, v: setitem(r, FakeService, Value(v)),
        ],
    )
    def test_register_value_defaults(self, register):
        svcs = Registry()
        value = FakeService()

        register(svcs, value)

        assert svcs.get_descriptor(FakeService) == ValueServiceDescriptor(
            value, enter=False
        )

    @pytest.mark.parametrize(
        "register",
        [
            lambda r, v, e: r.register_value(FakeService, v, enter=e),
            lambda r, v, e: r.register(FakeService, Value(v, enter=e)),
            lambda r, v, e: setitem(r, FakeService, Value(v, enter=e)),
        ],
    )
    @use_enter
    def test_register_value(self, register, enter):
        svcs = Registry()
        value = FakeService()

        register(svcs, value, enter)

        assert svcs.get_descriptor(FakeService) == ValueServiceDescriptor(
            value, enter=enter
        )


class TestExplicitRegistration:
    @use_factories
    @use_lifetimes
    def test_register_factory(
        self, factory: ServiceFactory[Any], lifetime: Lifetime
    ) -> None:
        svcs = Registry()

        ret = svcs.register_factory(FakeService, factory, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, factory, lifetime=lifetime)

    @use_lifetimes
    def test_register_factory_without_factory_defaults_to_service_type(
        self, lifetime: Lifetime
    ) -> None:
        svcs = Registry()

        ret = svcs.register_factory(FakeService, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, FakeService, lifetime=lifetime)

    @use_factories
    def test_register_singleton(self, factory: ServiceFactory[Any]) -> None:
        svcs = Registry()

        ret = svcs.register_singleton(FakeService, factory)

        assert ret is svcs
        assert_has_singleton_descriptor(svcs, FakeService, factory)

    def test_register_singleton_without_factory_defaults_to_service_type(self) -> None:
        svcs = Registry()

        ret = svcs.register_singleton(FakeService)

        assert ret is svcs
        assert_has_singleton_descriptor(svcs, FakeService, FakeService)

    @use_factories
    def test_register_scoped(self, factory: ServiceFactory[Any]) -> None:
        svcs = Registry()

        ret = svcs.register_scoped(FakeService, factory)

        assert ret is svcs
        assert_has_scoped_descriptor(svcs, FakeService, factory)

    def test_register_scoped_without_factory_defaults_to_service_type(self) -> None:
        svcs = Registry()

        ret = svcs.register_scoped(FakeService)

        assert ret is svcs
        assert_has_scoped_descriptor(svcs, FakeService, FakeService)

    def test_register_value(self) -> None:
        svcs = Registry()
        fake = FakeService()

        ret = svcs.register_value(FakeService, fake)

        assert ret is svcs
        assert_has_value_descriptor(svcs, FakeService, fake)

    def test_register_alias(self) -> None:
        svcs = Registry()

        ret = svcs.register_alias(FakeService, FakeService)

        assert ret is svcs
        assert_has_alias_descriptor(svcs, FakeService, FakeService)


class TestImplicitRegistration:
    def test_register_a_descriptor_registers_it_as_is(self) -> None:
        svcs = Registry()
        descriptor = FactoryServiceDescriptor(FakeService)

        ret = svcs.register(FakeService, descriptor)

        assert ret is svcs
        assert_has_descriptor(svcs, FakeService, descriptor)

    def test_register_a_type_registers_an_alias_descriptor(self) -> None:
        svcs = Registry()

        ret = svcs.register(FakeService, FakeServiceImpl)

        assert ret is svcs
        assert_has_alias_descriptor(svcs, FakeService, FakeServiceImpl)

    @use_lifetimes
    def test_register_a_function_registers_a_factory_descriptor(
        self, lifetime: Lifetime
    ) -> None:
        svcs = Registry()

        def factory() -> FakeService:
            return FakeService()

        ret = svcs.register(FakeService, factory, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, factory, lifetime=lifetime)

    def test_register_a_non_callable_registers_a_value(self) -> None:
        svcs = Registry()
        fake = FakeService()

        ret = svcs.register(FakeService, fake)

        assert ret is svcs
        assert_has_value_descriptor(svcs, FakeService, fake)

    @use_lifetimes
    def test_register_a_service_without_descriptor_registers_a_factory_using_service_type_itself(
        self, lifetime: Lifetime
    ) -> None:
        svcs = Registry()

        ret = svcs.register(FakeService, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, FakeService, lifetime=lifetime)


class TestDictLikeRegistration:
    def test_set_a_descriptor_registers_it_as_is(self) -> None:
        svcs = Registry()
        descriptor = FactoryServiceDescriptor(FakeService)

        svcs[FakeService] = descriptor

        assert_has_descriptor(svcs, FakeService, descriptor)

    def test_set_a_type_registers_an_alias_descriptor(self) -> None:
        svcs = Registry()

        svcs[FakeService] = FakeServiceImpl

        assert_has_alias_descriptor(svcs, FakeService, FakeServiceImpl)

    def test_set_a_function_registers_a_factory_descriptor(self) -> None:
        svcs = Registry()

        svcs[FakeService] = fake_service_factory

        assert_has_factory_descriptor(svcs, FakeService, fake_service_factory)

    def test_set_a_non_callable_registers_a_value_descriptor(self) -> None:
        svcs = Registry()
        fake = FakeService()

        svcs[FakeService] = fake

        assert_has_value_descriptor(svcs, FakeService, fake)

    def test_set_an_ellipsis_registers_the_type_itself_as_a_factory_descriptor(
        self,
    ) -> None:
        svcs = Registry()

        svcs[FakeService] = ...

        assert_has_factory_descriptor(svcs, FakeService, FakeService)


class TestDecoratorRegistration:
    def test_factory_decorator_requires_return_type_annotation(self) -> None:
        svcs = Registry()

        with pytest.raises(RegistrationError):

            @svcs.factory
            def non_typed_factory():  # type: ignore[no-untyped-def]
                return FakeService()

    def test_factory_decorator_registers_a_factory(self) -> None:
        svcs = Registry()

        @svcs.factory
        def some_factory() -> FakeService:
            return FakeService()

        @svcs.factory()
        def object_factory() -> object:
            return object()

        assert_has_factory_descriptor(svcs, FakeService, some_factory)
        assert_has_factory_descriptor(svcs, object, object_factory)

    @use_lifetimes
    def test_factory_decorator_factory_registers_a_factory(
        self, lifetime: Lifetime
    ) -> None:
        svcs = Registry()

        @svcs.factory(lifetime=lifetime)
        def some_factory() -> FakeService:
            return FakeService()

        assert_has_factory_descriptor(
            svcs, FakeService, some_factory, lifetime=lifetime
        )

    def test_singleton_decorator_registers_a_singleton(self) -> None:
        svcs = Registry()

        @svcs.singleton
        def some_factory() -> FakeService:
            return FakeService()

        @svcs.singleton()
        def some_other_factory() -> FakeServiceImpl:
            return FakeServiceImpl()

        assert_has_singleton_descriptor(svcs, FakeService, some_factory)
        assert_has_singleton_descriptor(svcs, FakeServiceImpl, some_other_factory)

    def test_scoped_decorator_registers_a_scoped_factory(self) -> None:
        svcs = Registry()

        @svcs.scoped
        def some_factory() -> FakeService:
            return FakeService()

        @svcs.scoped()
        def object_factory() -> object:
            return FakeService()

        assert_has_scoped_descriptor(svcs, FakeService, some_factory)
        assert_has_scoped_descriptor(svcs, object, object_factory)

    def test_factory_decorator_resolve_forward_ref_return_type_annotation(self) -> None:
        svcs = Registry()

        @svcs.factory
        def some_factory() -> "FakeService":
            return FakeService()

        assert_has_factory_descriptor(svcs, FakeService, some_factory)
