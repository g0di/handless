from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, LifetimeLiteral, Registry
from handless._lifetimes import Transient
from handless._lifetimes import parse as parse_lifetime
from handless.exceptions import RegistrationAlreadyExistingError
from handless.providers import Alias, Dynamic, Factory, Value
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
        sut.bind(FakeService).to_self()

        assert sut.lookup(FakeService) == Binding(
            FakeService, Factory(FakeService), lifetime=Transient()
        )

    @use_enter
    @use_lifetimes
    def test_register_none_and_options_registers_a_factory_with_given_options_using_given_type(
        self, sut: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        sut.bind(FakeService).to_self(enter=enter, lifetime=lifetime)

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            Factory(FakeService),
            enter=enter,
            lifetime=parse_lifetime(lifetime),
        )


class TestRegisterType:
    def test_register_type_registers_an_alias(self, sut: Registry) -> None:
        sut.bind(IFakeService).to(FakeService)  # type: ignore[type-abstract]

        assert sut.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService,  # type: ignore[type-abstract]
            Alias(FakeService),
            enter=False,
        )


class TestRegisterObject:
    @pytest.mark.parametrize("type_", [IFakeService, FakeService, FakeServiceNewType])
    @pytest.mark.parametrize("value", [FakeService(), CallableFakeService()])
    def test_register_object_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, type_: type[IFakeService], value: FakeService
    ) -> None:
        sut.bind(type_).to_value(value)

        assert sut.lookup(type_) == Binding(
            type_, Value(value), lifetime=parse_lifetime("singleton"), enter=False
        )

    @use_enter
    def test_register_object_with_enter_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, enter: bool
    ) -> None:
        sut.bind(FakeService).to_value(value := FakeService(), enter=enter)

        assert sut.lookup(FakeService) == Binding(
            FakeService, Value(value), lifetime=parse_lifetime("singleton"), enter=enter
        )


class TestRegisterFunction:
    def test_register_function_without_arguments_binds_given_type_to_given_function(
        self, sut: Registry
    ) -> None:
        my_factory = lambda: FakeService()  # noqa: E731
        sut.bind(FakeService).to_factory(my_factory)

        assert sut.lookup(FakeService) == Binding(FakeService, Factory(my_factory))

    def test_register_function_with_a_single_argument_binds_given_type_to_given_function_with_container_as_first_param(
        self, sut: Registry
    ) -> None:
        sut.bind(IFakeService).to_dynamic(  # type: ignore[type-abstract]
            factory := (lambda c: c.resolve(FakeService))
        )

        assert sut.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService, Dynamic(factory)
        )

    @use_enter
    @use_lifetimes
    def test_register_function_with_options_binds_given_type_to_given_function_and_options(
        self, sut: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        sut.bind(FakeService).to_factory(
            factory := lambda: FakeService(), enter=enter, lifetime=lifetime
        )

        assert sut.lookup(FakeService) == Binding(
            FakeService,
            Factory(factory),
            enter=enter,
            lifetime=parse_lifetime(lifetime),
        )

    @use_invalid_factory_provider
    def test_register_untyped_function_raises_an_error(
        self, sut: Registry, function: Callable[..., FakeService]
    ) -> None:
        with pytest.raises(TypeError):
            sut.bind(FakeService).to_factory(function)

    def test_register_generator_function_wraps_it_as_a_context_manager(
        self, sut: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        sut.bind(FakeService).to_factory(fake_service_generator)

        assert sut.lookup(FakeService) == Binding(
            FakeService, Factory(contextmanager(fake_service_generator))
        )

    def test_register_context_manager_function_registers_it_as_is(
        self, sut: Registry
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        sut.bind(FakeService).to_factory(fake_service_context_manager)

        assert sut.lookup(FakeService) == Binding(
            FakeService, Factory(fake_service_context_manager)
        )


def test_register_same_type_twice_raises_an_error_by_default(sut: Registry) -> None:
    sut.bind(object).to_value(object())

    with pytest.raises(RegistrationAlreadyExistingError):
        sut.bind(object).to_value(object())


@pytest.mark.registry_options(allow_direct_overrides=True)
def test_register_same_type_twice_do_not_raises_an_error_when_registry_allow_direct_overrides(
    sut: Registry,
) -> None:
    sut.bind(object).to_value(object())

    try:
        sut.bind(object).to_value(object())
    except RegistrationAlreadyExistingError:
        pytest.fail(reason="Registry should allow overriding existing bindings")
