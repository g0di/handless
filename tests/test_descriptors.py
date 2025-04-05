from inspect import Parameter
from typing import Callable

import pytest
from typing_extensions import Any

from handless import Lifetime, Provider
from tests import helpers


class TestValueProvider:
    def test_for_value_returns_a_singleton_provider_returning_given_value(self) -> None:
        value = object()

        provider = Provider.for_value(value)

        assert provider == Provider(lambda: value, enter=False, lifetime="singleton")

    @helpers.use_enter
    def test_for_value_with_options_returns_a_singleton_provider_with_given_options_returning_given_value(
        self, enter: bool
    ) -> None:
        value = object()

        provider = Provider.for_value(value, enter=enter)

        assert provider == Provider(lambda: value, enter=enter, lifetime="singleton")


@helpers.use_valid_provider_factory
class TestFactoryProvider:
    def test_for_factory_returns_a_transient_provider_with_given_function(
        self, factory: Callable[..., helpers.IFakeService]
    ) -> None:
        provider = Provider.for_factory(factory)

        assert provider == Provider(factory, lifetime="transient", enter=True)

    @helpers.use_lifetimes
    @helpers.use_enter
    def test_for_factory_with_options_returns_a_transient_provider_with_given_options(
        self,
        factory: Callable[..., helpers.IFakeService],
        lifetime: Lifetime,
        enter: bool,
    ) -> None:
        provider = Provider.for_factory(factory, lifetime=lifetime, enter=enter)

        assert provider == Provider(factory, lifetime=lifetime, enter=enter)


class TestProvider:
    def test_provider_defaults(self) -> None:
        provider = Provider(helpers.FakeService)

        assert provider.lifetime == "transient"
        assert provider.enter

    @helpers.use_invalid_provider_factory
    def test_provider_with_invalid_callable_raises_an_error(
        self, factory: Callable[..., Any]
    ) -> None:
        with pytest.raises(TypeError):
            Provider(factory)


class TestAliasProvider:
    def test_for_alias_returns_a_transient_provider_with_function_having_given_type_as_param_and_returns_it(
        self,
    ) -> None:
        provider = Provider.for_alias(object)

        assert provider == Provider(
            lambda x: x,
            lifetime="transient",
            enter=False,
            params=(
                Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=object),
            ),
        )
