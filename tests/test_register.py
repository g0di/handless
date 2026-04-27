from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import pytest

from handless import Binding, Container, Scope
from handless._registry import Dependency
from handless._utils import are_functions_equal
from handless.exceptions import BindingAlreadyExistsError, BindingError
from handless.lifetimes import Lifetime, Singleton, Transient
from tests.helpers import (
    FakeService,
    FakeServiceNewType,
    FakeServiceWithOneParam,
    FakeServiceWithParams,
    FakeServiceWithUntypedParams,
    IFakeService,
    create_fake_service,
    create_fake_service_with_params,
    create_fake_service_with_untyped_params,
    use_lifetimes,
    use_managed,
)


class TestBindFactory:
    @pytest.mark.parametrize(
        ("factory", "dependencies"),
        [
            pytest.param(FakeService, (), id="Type"),
            pytest.param(lambda: FakeService(), (), id="Lambda"),
            pytest.param(create_fake_service, (), id="Function"),
            pytest.param(
                FakeServiceWithParams,
                (Dependency("foo", str), Dependency("bar", int)),
                id="Type with arguments",
            ),
            pytest.param(
                FakeServiceWithOneParam,
                (Dependency("foo", str),),
                id="Type with one argument",
            ),
            pytest.param(
                lambda ctx: FakeServiceWithParams(ctx.resolve(str), ctx.resolve(int)),
                (Dependency("ctx", Scope),),
                id="Lambda with single argument",
            ),
            pytest.param(
                create_fake_service_with_params,
                (Dependency("foo", str), Dependency("bar", int, default=5)),
                id="Function with arguments",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "type_",
        [IFakeService, FakeService, FakeServiceNewType],
        ids=["Protocol", "Type", "NewType"],
    )
    def test_bind_factory(
        self,
        container: Container,
        type_: type[IFakeService],
        factory: Callable[..., IFakeService],
        dependencies: tuple[Dependency, ...],
    ) -> None:
        container.bind(type_).to_factory(factory)

        assert container.lookup(type_) == Binding(
            type_,
            factory,
            managed=True,
            lifetime=Transient(),
            dependencies=dependencies,
        )

    @pytest.mark.parametrize(
        "factory",
        [
            pytest.param(FakeServiceWithUntypedParams, id="Type"),
            pytest.param(lambda foo, bar: FakeServiceWithParams(foo, bar), id="Lambda"),
            pytest.param(create_fake_service_with_untyped_params, id="Function"),
        ],
    )
    def test_bind_factory_with_untyped_parameters(
        self, container: Container, factory: Callable[..., FakeServiceWithParams]
    ) -> None:
        with pytest.raises(BindingError):
            container.bind(FakeServiceWithParams).to_factory(factory)

    @use_managed
    @use_lifetimes
    def test_bind_factory_with_options(
        self,
        container: Container,
        managed: bool,
        lifetime: Lifetime | type[Lifetime],
        expected_lifetime: Lifetime,
    ) -> None:
        container.bind(FakeService).to_factory(FakeService, lifetime, managed=managed)

        assert container.lookup(FakeService) == Binding(
            FakeService, FakeService, managed=managed, lifetime=expected_lifetime
        )

    def test_bind_factory_with_generator_function_wraps_it_as_a_context_manager(
        self, container: Container
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        container.bind(FakeService).to_factory(fake_service_generator)

        assert container.lookup(FakeService) == Binding(
            FakeService,
            contextmanager(fake_service_generator),
            managed=True,
            lifetime=Transient(),
        )

    def test_bind_factory_with_async_generator_function_wraps_it_as_an_async_context_manager(
        self, container: Container
    ) -> None:
        async def fake_service_generator() -> AsyncIterator[FakeService]:
            yield FakeService()

        container.bind(FakeService).to_factory(fake_service_generator)

        assert container.lookup(FakeService) == Binding(
            FakeService,
            asynccontextmanager(fake_service_generator),
            managed=True,
            lifetime=Transient(),
        )

    def test_bind_factory_with_contextmanager_decorated_function_binds_it_as_is(
        self, container: Container
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        container.bind(FakeService).to_factory(fake_service_context_manager)

        assert container.lookup(FakeService).factory == fake_service_context_manager

    def test_bind_factory_with_asynccontextmanager_decorated_function_binds_it_as_is(
        self, container: Container
    ) -> None:
        @asynccontextmanager
        async def fake_service_context_manager() -> AsyncIterator[FakeService]:
            yield FakeService()

        container.bind(FakeService).to_factory(fake_service_context_manager)

        assert container.lookup(FakeService).factory == fake_service_context_manager


class TestBindValue:
    def test_bind_value(self, container: Container) -> None:
        container.bind(FakeService).to_value(expected := FakeService())

        assert container.lookup(FakeService) == Binding(
            FakeService, lambda: expected, managed=False, lifetime=Singleton()
        )

    @use_managed
    def test_bind_value_with_options(self, container: Container, managed: bool) -> None:
        container.bind(FakeService).to_value(FakeService(), managed=managed)

        assert container.lookup(FakeService).managed is managed


class TestBindAlias:
    def test_bind_alias(self, container: Container) -> None:
        container.bind(IFakeService).to(alias := FakeService)  # type: ignore[type-abstract]

        assert container.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            lambda c: c.resolve(alias),
            lifetime=Transient(),
            managed=False,
            dependencies=(Dependency("c", Scope),),
        )


class TestBindSelf:
    def test_bind_self(self, container: Container) -> None:
        container.bind(FakeService).to_self()

        assert container.lookup(FakeService) == Binding(
            FakeService, FakeService, lifetime=Transient(), managed=True
        )

    @use_managed
    @use_lifetimes
    def test_bind_self_with_options(
        self,
        container: Container,
        managed: bool,
        lifetime: Lifetime | type[Lifetime],
        expected_lifetime: Lifetime,
    ) -> None:
        container.bind(FakeService).to_self(lifetime, managed=managed)

        assert container.lookup(FakeService) == Binding(
            FakeService, FakeService, lifetime=expected_lifetime, managed=managed
        )


class TestBindFactoryUsingDecorator:
    def test_factory_decorator_binds_decorated_function_for_its_return_type_annotation(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service() -> FakeService:
            return FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService, get_fake_service, managed=True, lifetime=Transient()
        )

    def test_factory_decorator_binds_decorated_function_with_arguments(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service(
            foo: str,  # noqa: ARG001
            ctx: Scope,  # noqa: ARG001
            *args: Any,  # noqa: ANN401, ARG001
            bar: int = 5,  # noqa: ARG001
            **kwargs: Any,  # noqa: ANN401, ARG001
        ) -> FakeService:
            return FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService,
            get_fake_service,
            managed=True,
            lifetime=Transient(),
            dependencies=(
                Dependency("foo", str),
                Dependency("ctx", Scope),
                Dependency("bar", int, default=5),
            ),
        )

    def test_factory_decorator_raise_error_for_function_with_untyped_parameters(
        self, container: Container
    ) -> None:
        with pytest.raises(BindingError):

            @container.factory
            def get_fake_service(foo, bar) -> FakeService:  # type: ignore  # noqa: ANN001, ARG001, PGH003
                return FakeService()

    def test_factory_decorator_raise_error_for_function_without_return_type(
        self, container: Container
    ) -> None:
        with pytest.raises(BindingError):

            @container.factory
            def get_fake_service():  # type: ignore  # noqa: ANN202, PGH003
                return FakeService()

    def test_factory_decorator_wraps_decorated_generators_as_context_manager(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService,
            contextmanager(get_fake_service),
            managed=True,
            lifetime=Transient(),
        )

    def test_factory_decorator_wraps_decorated_async_generators_as_async_context_manager(
        self, container: Container
    ) -> None:
        @container.factory
        async def get_fake_service() -> AsyncIterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService,
            asynccontextmanager(get_fake_service),
            managed=True,
            lifetime=Transient(),
        )

    def test_factory_decorator_binds_context_manager_as_is(
        self, container: Container
    ) -> None:
        @container.factory
        @contextmanager
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService, get_fake_service, managed=True, lifetime=Transient()
        )

    def test_factory_decorator_binds_async_context_manager_as_is(
        self, container: Container
    ) -> None:
        @container.factory
        @asynccontextmanager
        async def get_fake_service() -> AsyncIterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Binding(
            FakeService, get_fake_service, managed=True, lifetime=Transient()
        )

    @use_managed
    @use_lifetimes
    def test_factory_decorator_with_options(
        self,
        container: Container,
        managed: bool,
        lifetime: Lifetime | type[Lifetime],
        expected_lifetime: Lifetime,
    ) -> None:
        @container.factory(lifetime=lifetime, managed=managed)
        def get_fake_service() -> FakeService:
            return FakeService()

        binding = container.lookup(FakeService)

        assert binding.managed is managed
        assert binding.lifetime == expected_lifetime


def test_bind_same_type_twice_raises_an_error(container: Container) -> None:
    container.bind(FakeService).to_value(FakeService())

    with pytest.raises(BindingAlreadyExistsError):
        container.bind(FakeService).to_value(FakeService())


def test_override_bound_type(container: Container) -> None:
    service = FakeService()
    container.bind(FakeService).to_value(service)

    container.override(FakeService).to_value(expected := FakeService())

    binding = container.lookup(FakeService)
    assert are_functions_equal(binding.factory, lambda: expected)
