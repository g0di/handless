from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, Container, LifetimeLiteral, Registry
from handless._bindings import Dependency
from handless._lifetimes import Lifetime, Singleton, Transient
from handless.exceptions import RegistrationAlreadyExistError
from tests.helpers import (
    FakeService,
    FakeServiceNewType,
    FakeServiceWithParams,
    IFakeService,
    use_enter,
    use_lifetimes,
)


class TestBindToProvider:
    @pytest.mark.parametrize(
        "service_type", [IFakeService, FakeService, FakeServiceNewType]
    )
    @pytest.mark.parametrize("factory", [FakeService, lambda: FakeService])
    def test_bind_type_to_provider(
        self,
        registry: Registry,
        service_type: type[IFakeService],
        factory: Callable[..., FakeService],
    ) -> None:
        registry.bind(service_type).to_provider(factory)

        received = registry.lookup(service_type)

        assert received == Binding(
            service_type, factory, enter=True, lifetime=Transient()
        )

    def test_bind_type_to_provider_with_params(self, registry: Registry) -> None:
        def my_factory(foo: str, /, bar: int = 42) -> FakeService: ...  # type: ignore[empty-body]

        registry.bind(FakeService).to_provider(my_factory)

        received = registry.lookup(FakeService)

        assert received == Binding(
            FakeService,
            my_factory,
            enter=True,
            lifetime=Transient(),
            dependencies={
                "foo": Dependency(str, positional=True),
                "bar": Dependency(int, default=42),
            },
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_provider_with_options(
        self,
        registry: Registry,
        enter: bool,
        lifetime_literal: LifetimeLiteral,
        lifetime: Lifetime,
    ) -> None:
        registry.bind(FakeService).to_provider(
            FakeService, enter=enter, lifetime=lifetime_literal
        )

        received = registry.lookup(FakeService)

        assert received == Binding(
            FakeService, FakeService, enter=enter, lifetime=lifetime
        )

    def test_bind_type_to_generator_function_wraps_it_as_a_context_manager(
        self, registry: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_provider(fake_service_generator)

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            contextmanager(fake_service_generator),
            enter=True,
            lifetime=Transient(),
        )

    def test_bind_type_to_contextmanager_decorated_function_registers_it_as_is(
        self, registry: Registry
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_provider(fake_service_context_manager)

        assert registry.lookup(FakeService).provider == fake_service_context_manager


class TestBindToFactory:
    def test_bind_type_to_factory(self, registry: Registry) -> None:
        registry.bind(FakeService).to_factory(expected := (lambda _: FakeService()))

        assert registry.lookup(FakeService) == Binding(
            type_=FakeService,
            provider=lambda container: expected(container),
            enter=True,
            lifetime=Transient(),
            dependencies={"container": Dependency(Container)},
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_factory_with_options(
        self,
        registry: Registry,
        enter: bool,
        lifetime_literal: LifetimeLiteral,
        lifetime: Lifetime,
    ) -> None:
        registry.bind(FakeService).to_factory(
            lambda _: FakeService(), enter=enter, lifetime=lifetime_literal
        )

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


class TestBindToValue:
    def test_bind_type_to_value(self, registry: Registry) -> None:
        registry.bind(FakeService).to_value(expected := FakeService())

        assert registry.lookup(FakeService) == Binding(
            FakeService, lambda: expected, enter=False, lifetime=Singleton()
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
            FakeService, FakeService, enter=True, lifetime=Transient()
        )

    def test_bind_type_to_self_with_params(self, registry: Registry) -> None:
        registry.bind(FakeServiceWithParams).to_self()

        assert registry.lookup(FakeServiceWithParams) == Binding(
            FakeServiceWithParams,
            FakeServiceWithParams,
            enter=True,
            lifetime=Transient(),
            dependencies={"foo": Dependency(str), "bar": Dependency(int)},
        )

    @use_enter
    @use_lifetimes
    def test_bind_type_to_self_with_options(
        self,
        registry: Registry,
        enter: bool,
        lifetime_literal: LifetimeLiteral,
        lifetime: Lifetime,
    ) -> None:
        registry.bind(FakeService).to_self(enter=enter, lifetime=lifetime_literal)

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


class TestBindToType:
    def test_bind_type_to_another_type(self, registry: Registry) -> None:
        registry.bind(IFakeService).to(FakeService)  # type: ignore[type-abstract]

        assert registry.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            lambda alias: alias,
            lifetime=Transient(),
            enter=False,
            dependencies={"alias": Dependency(FakeService)},
        )


class TestBindToProviderDecorator:
    def test_provider_decorator(self, registry: Registry) -> None:
        @registry.provider
        def get_fake_service() -> FakeService:
            return FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    def test_provider_decorator_with_params(self, registry: Registry) -> None:
        @registry.provider
        def get_fake_service(foo: str, bar: int) -> FakeService:  # noqa: ARG001
            return FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            get_fake_service,
            enter=True,
            lifetime=Transient(),
            dependencies={"foo": Dependency(str), "bar": Dependency(int)},
        )

    def test_provider_decorator_with_generator_function(
        self, registry: Registry
    ) -> None:
        @registry.provider
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            contextmanager(get_fake_service),
            enter=True,
            lifetime=Transient(),
        )

    def test_provider_decorator_with_context_manager_function(
        self, registry: Registry
    ) -> None:
        @registry.provider
        @contextmanager
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert registry.lookup(FakeService) == Binding(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    @use_enter
    @use_lifetimes
    def test_provider_decorator_with_options(
        self,
        registry: Registry,
        enter: bool,
        lifetime_literal: LifetimeLiteral,
        lifetime: Lifetime,
    ) -> None:
        @registry.provider(lifetime=lifetime_literal, enter=enter)
        def get_fake_service() -> FakeService:
            return FakeService()

        binding = registry.lookup(FakeService)

        assert binding.enter is enter
        assert binding.lifetime == lifetime


def test_register_binding(registry: Registry) -> None:
    binding = Binding(FakeService, FakeService, enter=True, lifetime=Singleton())

    registry.register(binding)

    assert registry.lookup(FakeService) is binding


def test_bind_same_type_twice_raises_an_error(registry: Registry) -> None:
    registry.bind(FakeService).to_value(FakeService())

    with pytest.raises(RegistrationAlreadyExistError):
        registry.bind(FakeService).to_self()
