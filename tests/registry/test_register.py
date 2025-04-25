from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypedDict

import pytest

from handless import Binding, Container, LifetimeLiteral, Registry
from handless.exceptions import RegistrationAlreadyExistError
from handless.providers import Provider
from tests.helpers import (
    FakeService,
    FakeServiceNewType,
    FakeServiceWithParams,
    IFakeService,
    use_enter,
    use_lifetimes,
)


class ValueOptions(TypedDict, total=False):
    enter: bool


class TestBindToFactory:
    @pytest.mark.parametrize(
        "service_type", [IFakeService, FakeService, FakeServiceNewType]
    )
    @pytest.mark.parametrize(
        "factory", [FakeService, lambda: FakeService, FakeServiceWithParams]
    )
    def test_bind_type_to_factory(
        self,
        registry: Registry,
        service_type: type[IFakeService],
        factory: Callable[..., FakeService],
    ) -> None:
        registry.bind(service_type).to_factory(factory)

        received = registry.lookup(service_type)

        assert received == Binding(
            service_type, Provider(factory), enter=True, lifetime="transient"
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_factory_with_options(
        self, registry: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        registry.bind(FakeService).to_factory(
            FakeService, enter=enter, lifetime=lifetime
        )

        received = registry.lookup(FakeService)

        assert received == Binding(
            FakeService, Provider(FakeService), enter=enter, lifetime=lifetime
        )

    def test_bind_type_to_generator_function_wraps_it_as_a_context_manager(
        self, registry: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_factory(fake_service_generator)

        assert registry.lookup(FakeService).provider == Provider(
            contextmanager(fake_service_generator)
        )

    def test_bind_type_to_contextmanager_decorated_function_registers_it_as_is(
        self, registry: Registry
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_factory(fake_service_context_manager)

        assert registry.lookup(FakeService).provider == Provider(
            fake_service_context_manager
        )


class TestBindToLambda:
    def test_bind_type_to_lambda(self, registry: Registry) -> None:
        registry.bind(FakeService).to_lambda(expected := (lambda _: FakeService()))

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            Provider(expected, params={"_": Container}),
            enter=True,
            lifetime="transient",
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_lambda_with_options(
        self, registry: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        registry.bind(FakeService).to_lambda(
            lambda _: FakeService(), enter=enter, lifetime=lifetime
        )

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


class TestBindToValue:
    def test_bind_type_to_value(self, registry: Registry) -> None:
        registry.bind(FakeService).to_value(expected := FakeService())

        assert registry.lookup(FakeService) == Binding(
            FakeService, Provider(lambda: expected), enter=False, lifetime="singleton"
        )

    @use_enter
    def test_bind_type_to_value_with_options(
        self, registry: Registry, enter: bool
    ) -> None:
        registry.bind(FakeService).to_value(FakeService(), enter=enter)

        assert registry.lookup(FakeService).enter is enter


class TestBindToSelf:
    def test_bind_type_to_self(self, registry: Registry) -> None:
        registry.bind(FakeService).to_self()

        assert registry.lookup(FakeService) == Binding(
            FakeService, Provider(FakeService), enter=True, lifetime="transient"
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_self_with_options(
        self, registry: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        registry.bind(FakeService).to_self(enter=enter, lifetime=lifetime)

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


class TestBindToType:
    def test_bind_type_to_another_type(self, registry: Registry) -> None:
        registry.bind(IFakeService).to(alias := FakeService)

        assert registry.lookup(IFakeService) == Binding(
            IFakeService,
            Provider(lambda c: c.get(alias), params={"c": Container}),
            lifetime="transient",
            enter=False,
        )


class TestBindToFactoryDecorator:
    def test_factory_decorator(self, registry: Registry) -> None:
        @registry.factory
        def get_fake_service() -> FakeService:
            return FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService, Provider(get_fake_service), enter=True, lifetime="transient"
        )

    def test_factory_decorator_with_generator_function(
        self, registry: Registry
    ) -> None:
        @registry.factory
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            Provider(contextmanager(get_fake_service)),
            enter=True,
            lifetime="transient",
        )

    def test_factory_decorator_with_context_manager_function(
        self, registry: Registry
    ) -> None:
        @registry.factory
        @contextmanager
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService, Provider(get_fake_service), enter=True, lifetime="transient"
        )

    @use_enter
    @use_lifetimes
    def test_factory_decorator_with_options(
        self, registry: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        @registry.factory(lifetime=lifetime, enter=enter)
        def get_fake_service() -> FakeService:
            return FakeService()

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime is lifetime


def test_register_binding(registry: Registry) -> None:
    binding = Binding(
        FakeService, Provider(FakeService), enter=True, lifetime="singleton"
    )

    registry.register(binding)

    assert registry.lookup(FakeService) is binding


def test_bind_same_type_twice_raises_an_error(registry: Registry) -> None:
    registry.bind(FakeService).to_value(FakeService())

    with pytest.raises(RegistrationAlreadyExistError):
        registry.bind(FakeService).to_value(FakeService())
