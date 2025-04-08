from inspect import Parameter
from typing import Callable

import pytest
from typing_extensions import Any

from handless import Binding, Lifetime
from tests import helpers


class TestValueBinding:
    def test_for_value_returns_a_singleton_binding_returning_given_value(self) -> None:
        value = object()

        binding = Binding.for_value(value)

        assert binding == Binding(lambda: value, enter=False, lifetime="singleton")

    @helpers.use_enter
    def test_for_value_with_options_returns_a_singleton_binding_with_given_options_returning_given_value(
        self, enter: bool
    ) -> None:
        value = object()

        binding = Binding.for_value(value, enter=enter)

        assert binding == Binding(lambda: value, enter=enter, lifetime="singleton")


@helpers.use_valid_provider
class TestFactoryBinding:
    def test_for_factory_returns_a_transient_binding_with_given_function(
        self, factory: Callable[..., helpers.IFakeService]
    ) -> None:
        binding = Binding.for_factory(factory)

        assert binding == Binding(factory, lifetime="transient", enter=True)

    @helpers.use_lifetimes
    @helpers.use_enter
    def test_for_factory_with_options_returns_a_transient_binding_with_given_options(
        self,
        factory: Callable[..., helpers.IFakeService],
        lifetime: Lifetime,
        enter: bool,
    ) -> None:
        binding = Binding.for_factory(factory, lifetime=lifetime, enter=enter)

        assert binding == Binding(factory, lifetime=lifetime, enter=enter)


class TestBinding:
    def test_binding_defaults(self) -> None:
        binding = Binding(helpers.FakeService)

        assert binding.lifetime == "transient"
        assert binding.enter

    @helpers.use_invalid_provider
    def test_binding_with_invalid_callable_raises_an_error(
        self, factory: Callable[..., Any]
    ) -> None:
        with pytest.raises(TypeError):
            Binding(factory)


class TestAliasBinding:
    def test_for_alias_returns_a_transient_binding_with_function_having_given_type_as_param_and_returns_it(
        self,
    ) -> None:
        binding = Binding.for_alias(object)

        assert binding == Binding(
            lambda x: x,
            lifetime="transient",
            enter=False,
            params=(
                Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=object),
            ),
        )
