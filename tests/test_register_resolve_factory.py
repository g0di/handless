from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from typing import Any
from unittest.mock import Mock

import pytest

from handless import Container, Registry


class ServiceWithContextManager(AbstractContextManager["ServiceWithContextManager"]):
    def __init__(self) -> None:
        self.entered = False
        self.exited = False
        self.reentered = False

    def __enter__(self) -> "ServiceWithContextManager":
        if self.entered:
            self.reentered = True
        self.entered = True
        return self

    def __exit__(self, *args: object) -> None:
        self.exited = True


class UntypedService:
    def __init__(self, foo, bar):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN204
        pass


untyped_lambda = lambda a, b, c: ...  # noqa: ARG005, E731


def untyped_function(foo, bar):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN201
    pass


@pytest.mark.parametrize(
    "untyped_callable", [untyped_function, untyped_lambda, UntypedService]
)
def test_register_factory_raise_an_error_for_untyped_callable(
    registry: Registry, untyped_callable: Callable[..., object]
) -> None:
    with pytest.raises(TypeError):
        registry.bind(object).to_factory(untyped_callable)


def test_register_factory_resolve_with_value_returned_by_given_factory(
    registry: Registry, container: Container
) -> None:
    value = object()
    object_factory = Mock(wraps=lambda: value)
    registry.bind(object).to_factory(object_factory)

    received = container.resolve(object)

    assert received is value
    object_factory.assert_called_once()


def test_register_factory_with_context_manager_resolve_by_entering_context_manager(
    registry: Registry, container: Container
) -> None:
    value = object()

    registry.bind(object).to_factory(lambda: nullcontext(value))

    received = container.resolve(object)

    assert received is value


def test_register_factory_with_context_manager_not_enter_context_if_enter_is_false(
    registry: Registry, container: Container
) -> None:
    value = ServiceWithContextManager()
    registry.bind(ServiceWithContextManager).to_factory(lambda: value, enter=False)

    received = container.resolve(ServiceWithContextManager)

    assert not received.entered


def test_register_factory_with_context_manager_not_being_instance_of_registered_type_disallow_enter_to_be_false(
    registry: Registry,
) -> None:
    # This test just ensure type checking
    registry.bind(str).to_factory(
        lambda: nullcontext("Hello World!"),  # type: ignore[arg-type, return-value]
        enter=False,
    )


def test_register_factory_with_params_resolve_its_params_before_calling_the_factory(
    registry: Registry, container: Container
) -> None:
    def object_factory(foo: str, bar: int) -> Any:  # noqa: ANN401
        return {"foo": foo, "bar": bar}

    registry.bind(str).to_value("Hello World!")
    registry.bind(int).to_value(42)
    registry.bind(object).to_factory(object_factory)

    received = container.resolve(object)

    assert received == {"foo": "Hello World!", "bar": 42}
