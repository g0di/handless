from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, LifetimeLiteral, Registry
from handless._lifetimes import parse as parse_lifetime
from handless.exceptions import RegistrationAlreadyExistingError
from handless.providers import Dynamic, Factory
from tests.helpers import (
    FakeService,
    IFakeService,
    use_enter,
    use_invalid_factory_provider,
    use_lifetimes,
)


class TestRegisterFunction:
    def test_register_function_without_arguments_binds_given_type_to_given_function(
        self, registry: Registry
    ) -> None:
        my_factory = lambda: FakeService()  # noqa: E731
        registry.bind(FakeService).to_factory(my_factory)

        assert registry.lookup(FakeService) == Binding(FakeService, Factory(my_factory))

    def test_register_function_with_a_single_argument_binds_given_type_to_given_function_with_container_as_first_param(
        self, registry: Registry
    ) -> None:
        registry.bind(IFakeService).to_dynamic(  # type: ignore[type-abstract]
            factory := (lambda c: c.resolve(FakeService))
        )

        assert registry.lookup(IFakeService) == Binding(  # type: ignore[type-abstract]
            IFakeService, Dynamic(factory)
        )

    @use_enter
    @use_lifetimes
    def test_register_function_with_options_binds_given_type_to_given_function_and_options(
        self, registry: Registry, enter: bool, lifetime: LifetimeLiteral
    ) -> None:
        registry.bind(FakeService).to_factory(
            factory := lambda: FakeService(), enter=enter, lifetime=lifetime
        )

        assert registry.lookup(FakeService) == Binding(
            FakeService,
            Factory(factory),
            enter=enter,
            lifetime=parse_lifetime(lifetime),
        )

    @use_invalid_factory_provider
    def test_register_untyped_function_raises_an_error(
        self, registry: Registry, function: Callable[..., FakeService]
    ) -> None:
        with pytest.raises(TypeError):
            registry.bind(FakeService).to_factory(function)

    def test_register_generator_function_wraps_it_as_a_context_manager(
        self, registry: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_factory(fake_service_generator)

        assert registry.lookup(FakeService) == Binding(
            FakeService, Factory(contextmanager(fake_service_generator))
        )

    def test_register_context_manager_function_registers_it_as_is(
        self, registry: Registry
    ) -> None:
        @contextmanager
        def fake_service_context_manager() -> Iterator[FakeService]:
            yield FakeService()

        registry.bind(FakeService).to_factory(fake_service_context_manager)

        assert registry.lookup(FakeService) == Binding(
            FakeService, Factory(fake_service_context_manager)
        )


def test_register_same_type_twice_raises_an_error_by_default(
    registry: Registry,
) -> None:
    registry.bind(object).to_value(object())

    with pytest.raises(RegistrationAlreadyExistingError):
        registry.bind(object).to_value(object())
