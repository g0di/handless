from contextlib import AbstractContextManager
from typing import TypedDict

import pytest

from handless import Container, Registry
from tests.helpers import FakeService


class FakeServiceProducer(AbstractContextManager[FakeService]):
    def __init__(self, enter_return: FakeService) -> None:
        self.enter_return = enter_return

    def __enter__(self) -> FakeService:
        return self.enter_return

    def __exit__(self, *args: object) -> None:
        pass


class ValueOptions(TypedDict, total=False):
    enter: bool


class TestRegisterResolveValue:
    def test_register_value_resolve_with_same_value(self) -> None:
        registry = Registry()
        registry.register(object).value(expected := object())
        container = Container(registry)

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
        self, options: ValueOptions, enter_expected: bool
    ) -> None:
        registry = Registry()
        registry.register(FakeService).value(FakeService(), **options)
        container = Container(registry)

        received = container.resolve(FakeService)

        assert received.entered is enter_expected

    def test_register_value_with_context_manager_of_different_type_and_enter_resolve_with_value_returned_by_its_enter_method(
        self,
    ) -> None:
        registry = Registry()
        registry.register(FakeService).value(
            FakeServiceProducer(expected := FakeService()), enter=True
        )
        container = Container(registry)

        received = container.resolve(FakeService)

        assert received is expected
