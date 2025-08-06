from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from handless import Container
from handless._registry import Dependency, Registration
from handless._utils import are_functions_equal
from handless.container import ResolutionContext
from handless.exceptions import RegistrationAlreadyExistError, RegistrationError
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
    use_enter,
    use_lifetimes,
)


class TestRegisterFactory:
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
                (Dependency("ctx", ResolutionContext),),
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
    def test_register_factory(
        self,
        container: Container,
        type_: type[IFakeService],
        factory: Callable[..., IFakeService],
        dependencies: tuple[Dependency, ...],
    ) -> None:
        container.register(type_).factory(factory)

        assert container.lookup(type_) == Registration(
            type_, factory, enter=True, lifetime=Transient(), dependencies=dependencies
        )

    @pytest.mark.parametrize(
        "factory",
        [
            pytest.param(FakeServiceWithUntypedParams, id="Type"),
            pytest.param(lambda foo, bar: FakeServiceWithParams(foo, bar), id="Lambda"),
            pytest.param(create_fake_service_with_untyped_params, id="Function"),
        ],
    )
    def test_register_factory_with_untyped_parameters(
        self, container: Container, factory: Callable[..., FakeServiceWithParams]
    ) -> None:
        with pytest.raises(RegistrationError):
            container.register(FakeServiceWithParams).factory(factory)

    @use_enter
    @use_lifetimes
    def test_register_factory_with_options(
        self, container: Container, enter: bool, lifetime: Lifetime
    ) -> None:
        container.register(FakeService).factory(
            FakeService, enter=enter, lifetime=lifetime
        )

        assert container.lookup(FakeService) == Registration(
            FakeService, FakeService, enter=enter, lifetime=lifetime
        )

    def test_register_factory_with_generator_function_wraps_it_as_a_context_manager(
        self, container: Container
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        container.register(FakeService).factory(fake_service_generator)

        assert container.lookup(FakeService) == Registration(
            FakeService,
            contextmanager(fake_service_generator),
            enter=True,
            lifetime=Transient(),
        )

    def test_register_factory_with_contextmanager_decorated_function_registers_it_as_is(
        self, container: Container
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        container.register(FakeService).factory(fake_service_context_manager)

        assert container.lookup(FakeService).factory == fake_service_context_manager


class TestRegisterValue:
    def test_register_value(self, container: Container) -> None:
        container.register(FakeService).value(expected := FakeService())

        assert container.lookup(FakeService) == Registration(
            FakeService, lambda: expected, enter=False, lifetime=Singleton()
        )

    @use_enter
    def test_register_value_with_options(
        self, container: Container, enter: bool
    ) -> None:
        container.register(FakeService).value(FakeService(), enter=enter)

        assert container.lookup(FakeService).enter is enter


class TestRegisterAlias:
    def test_register_alias(self, container: Container) -> None:
        container.register(IFakeService).alias(alias := FakeService)  # type: ignore[type-abstract]

        assert container.lookup(IFakeService) == Registration(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            lambda c: c.resolve(alias),
            lifetime=Transient(),
            enter=False,
            dependencies=(Dependency("c", ResolutionContext),),
        )


class TestRegisterSelf:
    def test_register_self(self, container: Container) -> None:
        container.register(FakeService).self()

        assert container.lookup(FakeService) == Registration(
            FakeService, FakeService, lifetime=Transient(), enter=True
        )

    @use_enter
    @use_lifetimes
    def test_register_self_with_options(
        self, container: Container, enter: bool, lifetime: Lifetime
    ) -> None:
        container.register(FakeService).self(lifetime=lifetime, enter=enter)

        assert container.lookup(FakeService) == Registration(
            FakeService, FakeService, lifetime=lifetime, enter=enter
        )


class TestRegisterFactoryUsingDecorator:
    def test_factory_decorator_register_decorated_function_for_its_return_type_annotation(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service() -> FakeService:
            return FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    def test_factory_decorator_register_decorated_function_with_arguments(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service(
            foo: str,  # noqa: ARG001
            ctx: ResolutionContext,  # noqa: ARG001
            *args: Any,  # noqa: ANN401, ARG001
            bar: int = 5,  # noqa: ARG001
            **kwargs: Any,  # noqa: ANN401, ARG001
        ) -> FakeService:
            return FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService,
            get_fake_service,
            enter=True,
            lifetime=Transient(),
            dependencies=(
                Dependency("foo", str),
                Dependency("ctx", ResolutionContext),
                Dependency("bar", int, default=5),
            ),
        )

    def test_factory_decorator_raise_error_for_function_with_untyped_parameters(
        self, container: Container
    ) -> None:
        with pytest.raises(RegistrationError):

            @container.factory
            def get_fake_service(foo, bar) -> FakeService:  # type: ignore  # noqa: ANN001, ARG001, PGH003
                return FakeService()

    def test_factory_decorator_raise_error_for_function_without_return_type(
        self, container: Container
    ) -> None:
        with pytest.raises(RegistrationError):

            @container.factory
            def get_fake_service():  # type: ignore  # noqa: ANN202, PGH003
                return FakeService()

    def test_factory_decorator_wraps_decorated_generators_as_context_manager(
        self, container: Container
    ) -> None:
        @container.factory
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService,
            contextmanager(get_fake_service),
            enter=True,
            lifetime=Transient(),
        )

    def test_factory_decorator_register_context_manager_as_is(
        self, container: Container
    ) -> None:
        @container.factory
        @contextmanager
        def get_fake_service() -> Iterator[FakeService]:
            yield FakeService()

        assert container.lookup(FakeService) == Registration(
            FakeService, get_fake_service, enter=True, lifetime=Transient()
        )

    @use_enter
    @use_lifetimes
    def test_factory_decorator_with_options(
        self, container: Container, enter: bool, lifetime: Lifetime
    ) -> None:
        @container.factory(lifetime=lifetime, enter=enter)
        def get_fake_service() -> FakeService:
            return FakeService()

        registration = container.lookup(FakeService)

        assert registration.enter is enter
        assert registration.lifetime == lifetime


def test_register_same_type_twice_raises_an_error(container: Container) -> None:
    container.register(FakeService).value(FakeService())

    with pytest.raises(RegistrationAlreadyExistError):
        container.register(FakeService).value(FakeService())


def test_override_registered_type(container: Container) -> None:
    service = FakeService()
    container.register(FakeService).value(service)

    container.override(FakeService).value(expected := FakeService())

    registration = container.lookup(FakeService)
    assert are_functions_equal(registration.factory, lambda: expected)
