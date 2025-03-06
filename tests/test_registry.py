import pytest
from typing_extensions import Any

from handless.descriptor import (
    AliasServiceDescriptor,
    Constant,
    Factory,
    FactoryServiceDescriptor,
    Lifetime,
    as_factory,
    as_impl,
    as_scoped,
    as_singleton,
    as_value,
)
from handless.registry import MissingReturnTypeAnnotationError, Registry
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


class TestServiceDescriptorFactories:
    def test_as_value_returns_a_value_descriptor(self) -> None:
        value = object()

        descriptor = as_value(value)

        assert descriptor == FactoryServiceDescriptor(
            Constant(value), lifetime="transient"
        )

    @use_factories
    @use_lifetimes
    def test_as_factory_returns_a_factory_descriptor(
        self, factory: Factory[Any], lifetime: Lifetime | None
    ) -> None:
        descriptor = as_factory(factory, lifetime=lifetime)

        assert descriptor == FactoryServiceDescriptor(
            factory, lifetime=lifetime or "transient"
        )

    @use_factories
    def test_as_singleton_returns_a_singleton_descriptor(
        self, factory: Factory[Any]
    ) -> None:
        descriptor = as_singleton(factory)

        assert descriptor == FactoryServiceDescriptor(factory, "singleton")

    @use_factories
    def test_as_scoped_returns_a_scoped_descriptor(self, factory: Factory[Any]) -> None:
        descriptor = as_scoped(factory)

        assert descriptor == FactoryServiceDescriptor(factory, "scoped")

    def test_as_impl_returns_a_descriptor_alias(self) -> None:
        descriptor = as_impl(FakeService)

        assert descriptor == AliasServiceDescriptor(FakeService)


class TestExplicitRegistration:
    @use_factories
    @use_lifetimes
    def test_register_factory(
        self, factory: Factory[Any], lifetime: Lifetime | None
    ) -> None:
        svcs = Registry()

        ret = svcs.register_factory(FakeService, factory, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, factory, lifetime=lifetime)

    @use_lifetimes
    def test_register_factory_without_factory_defaults_to_service_type(
        self, lifetime: Lifetime | None
    ) -> None:
        svcs = Registry()

        ret = svcs.register_factory(FakeService, lifetime=lifetime)

        assert ret is svcs
        assert_has_factory_descriptor(svcs, FakeService, FakeService, lifetime=lifetime)

    @use_factories
    def test_register_singleton(self, factory: Factory[Any]) -> None:
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
    def test_register_scoped(self, factory: Factory[Any]) -> None:
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

    def test_register_impl(self) -> None:
        svcs = Registry()

        ret = svcs.register_impl(FakeService, FakeService)

        assert ret is svcs
        assert_has_alias_descriptor(svcs, FakeService, FakeService)

    def test_register_impl_with_not_a_subclass_raise_an_error(self) -> None:
        svcs = Registry()

        with pytest.raises(TypeError):
            svcs.register_impl(FakeService, object)


class TestImplicitRegistration:
    def test_register_a_descriptor_registers_it_as_is(self) -> None:
        svcs = Registry()
        descriptor = FactoryServiceDescriptor(FakeService)

        ret = svcs.register(FakeService, descriptor)

        assert ret is svcs
        assert_has_descriptor(svcs, FakeService, descriptor)

    def test_register_a_type_registers_an_implementation(self) -> None:
        svcs = Registry()

        ret = svcs.register(FakeService, FakeServiceImpl)

        assert ret is svcs
        assert_has_alias_descriptor(svcs, FakeService, FakeServiceImpl)

    @use_lifetimes
    def test_register_a_non_type_callable_registers_a_factory(
        self, lifetime: Lifetime | None
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
        self, lifetime: Lifetime | None
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

    def test_set_a_type_registers_an_implementation(self) -> None:
        svcs = Registry()

        svcs[FakeService] = FakeServiceImpl

        assert_has_alias_descriptor(svcs, FakeService, FakeServiceImpl)

    def test_set_a_callable_registers_a_factory(self) -> None:
        svcs = Registry()

        svcs[FakeService] = fake_service_factory

        assert_has_factory_descriptor(svcs, FakeService, fake_service_factory)

    def test_set_a_non_callable_registers_a_value(self) -> None:
        svcs = Registry()
        fake = FakeService()

        svcs[FakeService] = fake

        assert_has_value_descriptor(svcs, FakeService, fake)


class TestDecoratorRegistration:
    def test_factory_decorator_requires_return_type_annotation(self) -> None:
        svcs = Registry()

        with pytest.raises(MissingReturnTypeAnnotationError):

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
        self, lifetime: Lifetime | None
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
