from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from handless import Container
from handless._registry import Registration
from handless.container import ResolutionContext
from handless.exceptions import RegistrationAlreadyExistError
from handless.lifetimes import Lifetime, Singleton, Transient
from tests.helpers import (
    FakeService,
    FakeServiceNewType,
    IFakeService,
    use_enter,
    use_lifetimes,
)


class TestBindToProvider:
    @pytest.mark.parametrize("type_", [IFakeService, FakeService, FakeServiceNewType])
    def test_bind_type_to_provider(
        self, container: Container, type_: type[IFakeService]
    ) -> None:
        container.register(type_).use_factory(provider := (lambda _: FakeService()))

        assert container.lookup(type_) == Registration(
            type_, provider, enter=True, lifetime=Transient()
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_provider_with_options(
        self, container: Container, enter: bool, lifetime: Lifetime
    ) -> None:
        container.register(FakeService).use_factory(
            provider := (lambda _: FakeService()), enter=enter, lifetime=lifetime
        )

        assert container.lookup(FakeService) == Registration(
            FakeService, provider, enter=enter, lifetime=lifetime
        )

    def test_bind_type_to_factory_without_arguments_wraps_it_as_a_provider(
        self, container: Container
    ) -> None:
        container.register(FakeService).use_factory(provider := FakeService)

        assert container.lookup(FakeService) == Registration(
            FakeService, lambda _: provider(), enter=True, lifetime=Transient()
        )

    def test_bind_type_to_generator_function_wraps_it_as_a_context_manager(
        self, container: Container
    ) -> None:
        def fake_service_generator(_: ResolutionContext) -> Iterator[FakeService]:
            yield FakeService()

        container.register(FakeService).use_factory(fake_service_generator)

        assert container.lookup(FakeService) == Registration(
            FakeService,
            contextmanager(fake_service_generator),
            enter=True,
            lifetime=Transient(),
        )

    def test_bind_type_to_contextmanager_decorated_function_registers_it_as_is(
        self, container: Container
    ) -> None:
        @contextmanager
        def fake_service_context_manager(_: ResolutionContext) -> Iterator[FakeService]:
            yield FakeService()

        container.register(FakeService).use_factory(fake_service_context_manager)

        assert container.lookup(FakeService).provider == fake_service_context_manager


class TestBindToValue:
    def test_bind_type_to_value(self, container: Container) -> None:
        container.register(FakeService).use_value(expected := FakeService())

        assert container.lookup(FakeService) == Registration(
            FakeService, lambda _: expected, enter=False, lifetime=Singleton()
        )

    @use_enter
    def test_bind_type_to_value_with_options(
        self, container: Container, enter: bool
    ) -> None:
        container.register(FakeService).use_value(FakeService(), enter=enter)

        assert container.lookup(FakeService).enter is enter


class TestBindToType:
    def test_bind_type_to_another_type(self, container: Container) -> None:
        container.register(IFakeService).use_alias(alias := FakeService)  # type: ignore[type-abstract]

        assert container.lookup(IFakeService) == Registration(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            lambda c: c.resolve(alias),
            lifetime=Transient(),
            enter=False,
        )


class TestBindToProviderDecorator:
    def test_provider_decorator(self, container: Container) -> None:
        @container.factory
        def get_fake_service(_: ResolutionContext) -> FakeService:
            return FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    def test_provider_decorator_with_generator_function(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service(_: ResolutionContext) -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService,
            contextmanager(get_fake_service),
            enter=True,
            lifetime=Transient(),
        )

    def test_provider_decorator_with_context_manager_function(
        self, container: Container
    ) -> None:
        @container.factory
        @contextmanager
        def get_fake_service(_: ResolutionContext) -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    @use_enter
    @use_lifetimes
    def test_provider_decorator_with_options(
        self, container: Container, enter: bool, lifetime: Lifetime
    ) -> None:
        @container.factory(lifetime=lifetime, enter=enter)
        def get_fake_service(_: ResolutionContext) -> FakeService:
            return FakeService()

        binding = container.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


def test_bind_same_type_twice_raises_an_error(container: Container) -> None:
    container.register(FakeService).use_value(FakeService())

    with pytest.raises(RegistrationAlreadyExistError):
        container.register(FakeService).use_value(FakeService())
