from contextlib import nullcontext
from typing import TypedDict

import pytest

from handless import Container, Registry
from tests.helpers import FakeService


class ValueOptions(TypedDict, total=False):
    enter: bool


def test_register_value_resolve_with_same_value(
    registry: Registry, container: Container
) -> None:
    registry.bind(object).to_value(expected := object())

    received = container.resolve(object)

    assert received is expected


@pytest.mark.parametrize(
    ("options", "enter_expected"),
    [
        (ValueOptions(), False),
        (ValueOptions(enter=False), False),
        (ValueOptions(enter=True), True),
    ],
)
def test_register_value_with_context_manager_do_not_enter_context_if_false_or_omitted(
    registry: Registry,
    container: Container,
    options: ValueOptions,
    enter_expected: bool,
) -> None:
    registry.bind(FakeService).to_value(FakeService(), **options)

    received = container.resolve(FakeService)

    assert received.entered is enter_expected


def test_register_value_with_context_manager_of_different_type_and_enter_resolve_with_value_returned_by_its_enter_method(
    registry: Registry, container: Container
) -> None:
    registry.bind(str).to_value(nullcontext("Hello World!"), enter=True)

    received = container.resolve(str)

    assert received == "Hello World!"


def test_register_value_with_context_manager_of_different_type_and_enter_false_is_not_allowed(
    registry: Registry,
) -> None:
    registry.bind(str).to_value(nullcontext("Hello World!"), enter=False)  # type: ignore[call-overload]
