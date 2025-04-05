from contextlib import contextmanager
from inspect import Parameter
from typing import Callable, Iterator

import pytest

from handless import Lifetime, Provider, Registry
from tests.helpers import (
    CallableFakeService,
    FakeService,
    FakeServiceNewType,
    IFakeService,
    use_enter,
    use_factory_function,
    use_invalid_factory_function,
    use_lifetimes,
)


@pytest.fixture
def sut() -> Registry:
    return Registry()


class TestRegisterSelf:
    def test_register_none_registers_a_transient_factory_using_given_type(
        self, sut: Registry
    ) -> None:
        registry = sut.register(FakeService)

        assert sut[FakeService] == Provider(FakeService)
        assert registry is sut

    @use_enter
    @use_lifetimes
    def test_register_none_and_options_registers_a_factory_with_given_options_using_given_type(
        self, sut: Registry, enter: bool, lifetime: Lifetime
    ) -> None:
        registry = sut.register(FakeService, enter=enter, lifetime=lifetime)

        assert sut[FakeService] == Provider(FakeService, enter=enter, lifetime=lifetime)
        assert registry is sut


class TestRegisterType:
    def test_register_type_registers_an_alias(self, sut: Registry) -> None:
        registry = sut.register(IFakeService, FakeService)  # type: ignore[type-abstract]

        assert sut[IFakeService] == Provider(
            lambda x: x,
            enter=False,
            params=(
                Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=FakeService),
            ),
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

        assert sut[IFakeService] == Provider(  # type: ignore[type-abstract]
            lambda x: x,
            enter=False,
            params=(
                Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=FakeService),
            ),
        )
        assert registry is sut


class TestRegisterObject:
    @pytest.mark.parametrize("type_", [IFakeService, FakeService, FakeServiceNewType])
    @pytest.mark.parametrize("value", [FakeService(), CallableFakeService()])
    def test_register_object_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, type_: type[IFakeService], value: FakeService
    ) -> None:
        registry = sut.register(type_, value)

        assert sut[type_] == Provider(lambda: value, lifetime="singleton", enter=False)
        assert registry is sut

    @use_enter
    def test_register_object_with_enter_binds_given_type_to_a_singleton_factory_of_given_object(
        self, sut: Registry, enter: bool
    ) -> None:
        registry = sut.register(FakeService, value := FakeService(), enter=enter)

        assert sut[FakeService] == Provider(
            lambda: value, lifetime="singleton", enter=enter
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

        assert sut[FakeService] == Provider(
            lambda: value, lifetime="singleton", enter=False
        )
        assert registry is sut


class TestRegisterFunction:
    @use_factory_function
    def test_register_function_binds_given_type_to_given_function(
        self, sut: Registry, function: Callable[..., FakeService]
    ) -> None:
        registry = sut.register(FakeService, function)

        assert sut[FakeService] == Provider(function)
        assert registry is sut

    @use_factory_function
    @use_enter
    @use_lifetimes
    def test_register_function_with_options_binds_given_type_to_given_function_and_options(
        self,
        sut: Registry,
        function: Callable[..., FakeService],
        enter: bool,
        lifetime: Lifetime,
    ) -> None:
        registry = sut.register(FakeService, function, enter=enter, lifetime=lifetime)

        assert sut[FakeService] == Provider(function, enter=enter, lifetime=lifetime)
        assert registry is sut

    @use_invalid_factory_function
    def test_register_untyped_function_raises_an_error(
        self, sut: Registry, function: Callable[..., FakeService]
    ) -> None:
        with pytest.raises(TypeError):
            sut.register(FakeService, function)

    def test_register_generator_function_wraps_it_as_a_context_manager(
        self, sut: Registry
    ) -> None:
        def fake_service_generator() -> Iterator[FakeService]:
            yield FakeService()

        registry = sut.register(FakeService, fake_service_generator)

        assert sut[FakeService] == Provider(
            contextmanager(fake_service_generator)  # type: ignore[arg-type]
        )
        assert registry is sut
