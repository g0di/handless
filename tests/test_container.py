from unittest.mock import Mock

import pytest

from handless.container import Container, ServiceNotFoundError, ServiceResolveError
from handless.registry import Registry
from tests.helpers import FakeService, FakeServiceFactory, FakeServiceImpl


class FakeServiceWithContextManager:
    entered: bool = False
    exited: bool = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args: object):
        self.exited = True


class TestResolvingUnregisteredServiceType:
    @pytest.mark.parametrize(
        "container",
        [Registry().create_container(), Registry().create_container().create_scope()],
        ids=["Root container", "Scoped container"],
    )
    def test_resolve_unregistered_service_type_raise_an_error(
        self, container: Container
    ):
        with pytest.raises(ServiceNotFoundError):
            container.resolve(object)


class TestResolvingValueDescriptor:
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


class TestResolveAnyFactoryDescriptorWithContextManager:
    def test_resolve_a_factory_descriptor_returning_context_manager_enter_context(
        self,
    ):
        value = FakeServiceWithContextManager()
        mock_factory = Mock(return_value=value)
        container = (
            Registry().register_factory(FakeService, mock_factory).create_container()
        )

        resolved = container.resolve(FakeService)

        assert resolved is value
        assert value.entered


class TestResolveAliasDescriptor:
    def test_resolve_an_alias_descriptor_resolves_the_actual_alias(self):
        container = (
            Registry()
            .register_factory(FakeServiceImpl)
            .register_impl(FakeService, FakeServiceImpl)
            .create_container()
        )

        resolved1 = container.resolve(FakeService)

        assert isinstance(resolved1, FakeServiceImpl)


class TestResolveTransientFactoryDescriptor:
    def test_resolve_a_transient_factory_descriptor_calls_factory_each_time(self):
        mock_factory = Mock()
        container = (
            Registry().register_factory(FakeService, mock_factory).create_container()
        )

        container.resolve(FakeService)
        container.resolve(FakeService)

        assert mock_factory.call_count == 2

    def test_resolve_a_transient_factory_descriptor_from_scope_calls_factory_each_time(
        self,
    ):
        mock_factory = Mock()
        container = (
            Registry().register_factory(FakeService, mock_factory).create_container()
        )
        scope = container.create_scope()

        container.resolve(FakeService)
        container.resolve(FakeService)
        scope.resolve(FakeService)
        scope.resolve(FakeService)

        assert mock_factory.call_count == 4


class TestResolveSingletonDescriptor:
    def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value(self):
        mock_factory = Mock(side_effect=object)
        container = (
            Registry().register_singleton(FakeService, mock_factory).create_container()
        )

        v1 = container.resolve(FakeService)
        v2 = container.resolve(FakeService)

        assert mock_factory.call_count == 1
        assert v1 is v2

    def test_resolve_a_singleton_descriptor_calls_and_cache_factory_return_value_accross_scopes(
        self,
    ):
        mock_factory = Mock(side_effect=object)
        container = (
            Registry().register_singleton(object, mock_factory).create_container()
        )
        scope = container.create_scope()

        v1 = container.resolve(object)
        v2 = container.resolve(object)
        v3 = scope.resolve(object)
        v4 = scope.resolve(object)

        assert mock_factory.call_count == 1
        assert v1 is v2 is v3 is v4


class TestResolvScopedFactoryDescrptor:
    def test_resolve_a_scoped_factory_descriptor_from_root_container_raise_an_error(
        self,
    ):
        mock_factory = Mock()
        container = (
            Registry().register_scoped(FakeService, mock_factory).create_container()
        )

        with pytest.raises(ServiceResolveError):
            container.resolve(FakeService)

        mock_factory.assert_not_called

    def test_resolve_a_scoped_factory_descriptor_calls_and_cache_factory_return_value_per_scope(
        self,
    ):
        mock_factory = Mock(side_effect=object)
        container = Registry().register_scoped(object, mock_factory).create_container()
        scope1 = container.create_scope()
        scope2 = container.create_scope()

        v1 = scope1.resolve(object)
        v2 = scope1.resolve(object)
        v3 = scope2.resolve(object)
        v4 = scope2.resolve(object)

        assert mock_factory.call_count == 2
        assert v1 is v2
        assert v3 is v4
        assert v1 is not v3

    # TODO: test closing a root container clear its cache (root container clear singletons, scoped containers clear scoped stuff)
    # TODO: test transient values entered as context manager are exited when the instance is no longer referenced
