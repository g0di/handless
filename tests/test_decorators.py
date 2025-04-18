from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager

import pytest

from handless import Binding, Container, LifetimeLiteral, Registry
from handless._lifetimes import parse as parse_lifetime
from handless.providers import Factory
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
    registry: Registry, function: Callable[..., FakeService]
) -> None:
    registry.factory(function)

    assert registry.lookup(FakeService) == Binding(FakeService, Factory(function))


def test_binding_decorator_registers_a_context_manager_decorated_function(
    registry: Registry,
) -> None:
    @registry.factory
    @contextmanager
    def create_fake_service() -> Iterator[FakeService]:
        yield FakeService()

    assert registry.lookup(FakeService) == Binding(
        FakeService, Factory(create_fake_service), enter=True
    )


@pytest.mark.parametrize(
    "function", [_create_fake_service_iterator, _create_fake_service_generator]
)
def test_binding_decorator_registers_generator_wrapped_as_context_manager(
    registry: Registry, function: Callable[[], Iterator[FakeService]]
) -> None:
    registry.factory(function)

    assert registry.lookup(FakeService) == Binding(
        FakeService, Factory(contextmanager(function))
    )


@use_enter
@use_lifetimes
def test_binding_decorator_registers_a_factory_binding_with_options(
    registry: Registry, enter: bool, lifetime: LifetimeLiteral
) -> None:
    registry.factory(lifetime=lifetime, enter=enter)(_create_fake_service_no_params)

    assert registry.lookup(FakeService) == Binding(
        FakeService,
        Factory(_create_fake_service_no_params),
        lifetime=parse_lifetime(lifetime),
        enter=enter,
    )
