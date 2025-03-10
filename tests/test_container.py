from unittest.mock import create_autospec

import pytest

from handless import Container, Registry
from handless.exceptions import ServiceNotFoundError, ServiceResolveError
from tests.helpers import FakeService, FakeServiceFactory, FakeServiceImpl


class TestResolveUnregisteredServiceType:
    @pytest.mark.parametrize(
        "container",
        [
            Container(Registry()),
            Container(Registry()).create_scope(),
        ],
        ids=["Root container", "Scoped container"],
    )
    def test_resolve_unregistered_service_type_use_a_transient_factory_by_default(
        self, container: Container
    ) -> None:
        resolved = container.resolve(FakeService)
        resolved2 = container.resolve(FakeService)

        assert isinstance(resolved, FakeService)
        assert isinstance(resolved2, FakeService)
        assert resolved is not resolved2

    @pytest.mark.parametrize(
        "container",
        [
            Container(Registry(), strict=True),
            Container(Registry(), strict=True).create_scope(),
        ],
        ids=["Strict root container", "Strict scoped container"],
    )
    def test_resolve_unregistered_service_type_raise_an_error_when_using_strict_model(
        self, container: Container
    ):
        with pytest.raises(ServiceNotFoundError):
            container.resolve(FakeService)


class TestResolveValueDescriptor:
    @pytest.fixture
    def value(self) -> FakeService:
        return FakeService()

    @pytest.fixture
    def container(self, value: FakeService) -> Container:
        return Registry().register_value(FakeService, value).create_container()

    def test_resolve_a_value_descriptor_returns_the_value(
        self, container: Container, value: FakeService
    ):
        resolved = container.resolve(FakeService)
        resolved2 = container.resolve(FakeService)

        assert resolved is value
        assert resolved2 is value

    def test_resolve_a_value_descriptor_from_scoped_container_returns_the_value(
        self, container: Container, value: FakeService
    ):
        scope = container.create_scope()

        resolved = container.resolve(FakeService)
        resolved2 = scope.resolve(FakeService)

        assert resolved is value
        assert resolved2 is value


class TestResolveAnyFactoryDescriptor:
    def test_resolve_a_factory_descriptor_using_a_function_calls_the_function(self):
        value1 = FakeService()

        def factory():
            return value1

        container = Registry().register_factory(FakeService, factory).create_container()

        resolved1 = container.resolve(FakeService)

        assert resolved1 is value1

    def test_resolve_a_factory_descriptor_using_a_class_creates_a_class_instance(self):
        container = (
            Registry().register_factory(FakeService, FakeServiceImpl).create_container()
        )

        resolved1 = container.resolve(FakeService)

        assert isinstance(resolved1, FakeServiceImpl)

    def test_resolve_a_factory_descriptor_using_a_callable_class_instance_calls_it(
        self,
    ):
        container = (
            Registry()
            .register_factory(FakeService, FakeServiceFactory())
            .create_container()
        )

        resolved1 = container.resolve(FakeService)

        assert isinstance(resolved1, FakeService)


class TestResolveAnyFactoryDescriptorWithParameters:
    def test_resolve_a_factory_descriptor_using_a_function_resolves_its_parameters(
        self,
    ):
        class ServiceB:
            pass

        class ServiceA:
            def __init__(self, b: ServiceB) -> None:
                self.b = b

        def service_a_factory(b: ServiceB):
            return ServiceA(b)

        container = (
            Registry()
            .register_value(ServiceB, expected := ServiceB())
            .register_factory(ServiceA, service_a_factory)
            .create_container()
        )

        resolved1 = container.resolve(ServiceA)

        assert resolved1.b is expected

    def test_resolve_a_factory_descriptor_using_a_class_resolves_its_parameters(self):
        class ServiceB:
            pass

        class ServiceA:
            def __init__(self, b: ServiceB) -> None:
                self.b = b

        container = (
            Registry()
            .register_value(ServiceB, expected := ServiceB())
            .register_factory(ServiceA)
            .create_container()
        )

        resolved1 = container.resolve(ServiceA)

        assert resolved1.b is expected

    def test_resolve_a_factory_descriptor_using_a_callable_class_instance_resolves_its_parameters(
        self,
    ):
        class ServiceB:
            pass

        class ServiceA:
            def __init__(self, b: ServiceB) -> None:
                self.b = b

        class ServiceAFactory:
            def __call__(self, b: ServiceB) -> ServiceA:
                return ServiceA(b)

        container = (
            Registry()
            .register_value(ServiceB, expected := ServiceB())
            .register_factory(ServiceA, ServiceAFactory())
            .create_container()
        )

        resolved1 = container.resolve(ServiceA)

        assert resolved1.b is expected

    def test_resolve_a_factory_descriptor_with_container_as_parameter_inject_current_container(
        self,
    ):
        def factory(c: Container):
            return c

        container = Registry().register_factory(object, factory).create_container()

        resolved = container.resolve(object)

        assert resolved is container

    def test_resolve_a_lambda_factory_descriptor_with_one_parameter_inject_current_container(
        self,
    ):
        lambda_factory = lambda c: c  # noqa: E731

        container = (
            Registry().register_factory(object, lambda_factory).create_container()
        )

        resolved = container.resolve(object)

        assert resolved is container

    # NOTE: we omit testing injecting container in classes constructors because we dont except any sane
    # people to put a container as a dependency of its own classes


class TestResolveAliasDescriptor:
    def test_resolve_an_alias_descriptor_resolves_the_actual_alias(self):
        container = (
            Registry()
            .register_factory(FakeServiceImpl)
            .register_alias(FakeService, FakeServiceImpl)
            .create_container()
        )

        resolved1 = container.resolve(FakeService)

        assert isinstance(resolved1, FakeServiceImpl)


class TestResolveTransientFactoryDescriptor:
    def test_resolve_a_transient_factory_descriptor_calls_factory_each_time(self):
        container = Registry().register_factory(FakeService).create_container()

        v1 = container.resolve(FakeService)
        v2 = container.resolve(FakeService)

        assert v1 is not v2

    def test_resolve_a_transient_factory_descriptor_from_scope_calls_factory_each_time(
        self,
    ):
        container = Registry().register_factory(FakeService).create_container()
        scope = container.create_scope()

        v1 = container.resolve(FakeService)
        v2 = container.resolve(FakeService)
        v3 = scope.resolve(FakeService)
        v4 = scope.resolve(FakeService)

        assert v1 is not v2 is not v3 is not v4


class TestResolveSingletonDescriptor:
    def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value(self):
        container = Registry().register_singleton(FakeService).create_container()

        v1 = container.resolve(FakeService)
        v2 = container.resolve(FakeService)

        assert v1 is v2

    def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value_accross_scopes(
        self,
    ):
        container = Registry().register_singleton(FakeService).create_container()
        scope = container.create_scope()

        v1 = container.resolve(FakeService)
        v2 = container.resolve(FakeService)
        v3 = scope.resolve(FakeService)
        v4 = scope.resolve(FakeService)

        assert v1 is v2 is v3 is v4


class TestResolveScopedFactoryDescrptor:
    def test_resolve_a_scoped_factory_descriptor_from_root_container_raise_an_error(
        self,
    ):
        mock_factory = create_autospec(lambda: FakeService())
        container = (
            Registry().register_scoped(FakeService, mock_factory).create_container()
        )

        with pytest.raises(ServiceResolveError):
            container.resolve(FakeService)

        mock_factory.assert_not_called

    def test_resolve_a_scoped_factory_descriptor_calls_and_cache_factory_returned_value_per_scope(
        self,
    ):
        registry = Registry().register_scoped(FakeService)
        container = Container(registry)
        scope1 = container.create_scope()
        scope2 = container.create_scope()

        v1 = scope1.resolve(FakeService)
        v2 = scope1.resolve(FakeService)
        v3 = scope2.resolve(FakeService)
        v4 = scope2.resolve(FakeService)

        assert v1 is v2
        assert v3 is v4
        assert v1 is not v3
