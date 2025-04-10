from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, Container, Lifetime, Registry
from handless._lifetime import TransientLifetime
from handless._lifetime import parse as parse_lifetime
from handless._provider import (
    AliasProvider,
    FactoryProvider,
    LambdaProvider,
    ValueProvider,
)
from handless.exceptions import BindingAlreadyExistingError
from tests.helpers import (
    CallableFakeService,
    FakeService,
    FakeServiceNewType,
    IFakeService,
    use_enter,
    use_invalid_factory_provider,
    use_lifetimes,
)


class TestRegisterSelf:
    def test_register_none_registers_a_transient_factory_using_given_type(
        self, sut: Registry
    ) -> None:
        registry = sut.register(FakeService)

        assert sut.lookup(FakeService) == Binding(
            FakeService, FactoryProvider(FakeService), lifetime=TransientLifetime()
        )
        assert registry is sut

    @use_enter
    @use_lifetimes
    def test_register_none_and_options_registers_a_factory_with_given_options_using_given_type(
        self, sut: Registry, enter: bool, lifetime: Lifetime
    ) -> None:
        registry = sut.register(FakeService, enter=enter, lifetime=lifetime)

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            FactoryProvider(FakeService),
            enter=enter,
            lifetime=parse_lifetime(lifetime),
        )
        assert registry is sut


class TestRegisterType:
    def test_register_type_registers_an_alias(self, sut: Registry) -> None:
        registry = sut.register(IFakeService, FakeService)  # type: ignore[type-abstract]

        assert sut.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            AliasProvider(FakeService),
            enter=False,
        )
        assert registry is sut

    @use_enter
    @use_lifetimes
    def test_register_type_with_options_registers_an_alias_and_raises_a_warning(
        self, sut: Registry, enter: bool, lifetime: Lifetime
    ) -> None:
        with pytest.warns(UserWarning):
            registry = sut.register(
                IFakeService,  # type: ignore[type-abstract]
                FakeService,
                enter=enter,
                lifetime=lifetime,
            )

        assert sut.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            AliasProvider(FakeService),
            enter=False,
        )
        assert registry is sut


class TestRegisterObject:
    @pytest.mark.parametrize("type_", [IFakeService, FakeService, FakeServiceNewType])
    @pytest.mark.parametrize("value", [FakeService(), CallableFakeService()])
    def test_register_object_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, type_: type[IFakeService], value: FakeService
    ) -> None:
        registry = sut.register(type_, value)

        assert sut.lookup(type_) == Binding(
            type_,
            ValueProvider(value),
            lifetime=parse_lifetime("singleton"),
            enter=False,
        )
        assert registry is sut

    @use_enter
    def test_register_object_with_enter_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, enter: bool
    ) -> None:
        registry = sut.register(FakeService, value := FakeService(), enter=enter)

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            ValueProvider(value),
            lifetime=parse_lifetime("singleton"),
            enter=enter,
        )
        assert registry is sut

    @use_lifetimes
    def test_register_object_with_lifetime_binds_given_type_to_a_singleton_factory_of_given_object_and_raises_warning(
        self, sut: Registry, lifetime: Lifetime
    ) -> None:
        with pytest.warns(UserWarning):
            registry = sut.register(
                FakeService, value := FakeService(), lifetime=lifetime
            )

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            ValueProvider(value),
            lifetime=parse_lifetime("singleton"),
            enter=False,
        )
        assert registry is sut


class TestRegisterFunction:
    def test_register_function_without_arguments_binds_given_type_to_given_function(
        self, sut: Registry
    ) -> None:
        my_factory = lambda: FakeService()  # noqa: E731
        registry = sut.register(FakeService, my_factory)

        assert sut.lookup(FakeService) == Binding(
            FakeService, FactoryProvider(my_factory)
        )
        assert registry is sut

    def test_register_function_with_a_single_argument_binds_given_type_to_given_function_with_container_as_first_param(
        self, sut: Registry
    ) -> None:
        registry = sut.register(
            IFakeService,  # type: ignore[type-abstract]
            factory := (lambda c: c.resolve(FakeService)),
        )

        assert sut.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService, LambdaProvider(factory)
        )
        assert registry is sut

    @use_enter
    @use_lifetimes
    def test_register_function_with_options_binds_given_type_to_given_function_and_options(
        self, sut: Registry, enter: bool, lifetime: Lifetime
    ) -> None:
        registry = sut.register(
            FakeService,
            factory := lambda: FakeService(),
            enter=enter,
            lifetime=lifetime,
        )

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            FactoryProvider(factory),
            enter=enter,
            lifetime=parse_lifetime(lifetime),
        )
        assert registry is sut

    @use_invalid_factory_provider
    def test_register_untyped_function_raises_an_error(
        self, sut: Registry, function: Callable[..., FakeService]
    ) -> None:
        with pytest.raises(TypeError):
            sut.register(FakeService, function)

    def test_register_generator_function_taking_container_wraps_it_as_a_context_manager(
        self, sut: Registry
    ) -> None:
        def fake_service_generator(container: Container) -> Iterator[FakeService]:  # noqa: ARG001
            yield FakeService()

        registry = sut.register(FakeService, fake_service_generator)

        assert sut.lookup(FakeService) == Binding(
            FakeService, LambdaProvider(contextmanager(fake_service_generator))
        )
        assert registry is sut

    def test_register_generator_function_wraps_it_as_a_context_manager(
        self, sut: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        registry = sut.register(FakeService, fake_service_generator)

        assert sut.lookup(FakeService) == Binding(
            FakeService, FactoryProvider(contextmanager(fake_service_generator))
        )
        assert registry is sut

    def test_register_context_manager_function_registers_it_as_is(
        self, sut: Registry
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        registry = sut.register(FakeService, fake_service_context_manager)

        assert sut.lookup(FakeService) == Binding(
            FakeService, FactoryProvider(fake_service_context_manager)
        )
        assert registry is sut


def test_register_same_type_twice_raises_an_error_by_default(sut: Registry) -> None:
    sut.register(object, object())

    with pytest.raises(BindingAlreadyExistingError):
        sut.register(object, object())


@pytest.mark.registry_options(allow_direct_overrides=True)
def test_register_same_type_twice_do_not_raises_an_error_when_registry_allow_direct_overrides(
    sut: Registry,
) -> None:
    sut.register(object, object())

    try:
        sut.register(object, object())
    except BindingAlreadyExistingError:
        pytest.fail(reason="Registry should allow overriding existing bindings")
