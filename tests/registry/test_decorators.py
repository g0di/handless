from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, Container, LifetimeLiteral, Registry
from handless._lifetime import parse as parse_lifetime
from handless._provider import Factory
from tests.helpers import FakeService, use_enter, use_lifetimes


def _create_fake_service_iterator() -> Iterator[FakeService]:
    yield FakeService()


def _create_fake_service_generator() -> Generator[FakeService, None, None]:
    yield FakeService()


def _create_fake_service_no_params() -> FakeService:
    return FakeService()


def _create_fake_service_container_param(container: Container) -> FakeService:  # noqa: ARG001
    return FakeService()


def _create_fake_service_params(foo: str, bar: int) -> FakeService:  # noqa: ARG001
    return FakeService()


@pytest.mark.parametrize(
    "function",
    [
        _create_fake_service_no_params,
        _create_fake_service_container_param,
        _create_fake_service_params,
    ],
)
def test_binding_decorator_registers_a_factory_binding(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    sut.binding(function)

    assert sut.lookup(FakeService) == Binding(FakeService, Factory(function))


def test_binding_decorator_registers_a_context_manager_decorated_function(
    sut: Registry,
) -> None:
    @sut.binding
    @contextmanager
    def create_fake_service() -> Iterator[FakeService]:
        yield FakeService()

    assert sut.lookup(FakeService) == Binding(
        FakeService, Factory(create_fake_service), enter=True
    )


@pytest.mark.parametrize(
    "function", [_create_fake_service_iterator, _create_fake_service_generator]
)
def test_binding_decorator_registers_generator_wrapped_as_context_manager(
    sut: Registry, function: Callable[[], Iterator[FakeService]]
) -> None:
    sut.binding(function)

    assert sut.lookup(FakeService) == Binding(
        FakeService, Factory(contextmanager(function))
    )


@use_enter
@use_lifetimes
def test_binding_decorator_registers_a_factory_binding_with_options(
    sut: Registry, enter: bool, lifetime: LifetimeLiteral
) -> None:
    sut.binding(lifetime=lifetime, enter=enter)(_create_fake_service_no_params)

    assert sut.lookup(FakeService) == Binding(
        FakeService,
        Factory(_create_fake_service_no_params),
        lifetime=parse_lifetime(lifetime),
        enter=enter,
    )
