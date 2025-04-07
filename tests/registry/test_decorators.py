from contextlib import contextmanager
from typing import Callable, Generator, Iterator

import pytest

from handless import Container, Lifetime, Provider, Registry
from tests.helpers import FakeService, use_enter, use_lifetimes


def _create_fake_service_iterator() -> Iterator[FakeService]:
    yield FakeService()


def _create_fake_service_generator() -> Generator[FakeService, None, None]:
    yield FakeService()


def _create_fake_service_no_params() -> FakeService:
    return FakeService()


def _create_fake_service_container_param(container: Container) -> FakeService:
    return FakeService()


def _create_fake_service_params(foo: str, bar: int) -> FakeService:
    return FakeService()


@pytest.mark.parametrize(
    "function",
    [
        _create_fake_service_no_params,
        _create_fake_service_container_param,
        _create_fake_service_params,
    ],
)
def test_provider_decorator_registers_a_factory_provider(
    sut: Registry, function: Callable[..., FakeService]
) -> None:
    sut.provider(function)

    assert sut[FakeService] == Provider(function)


@pytest.mark.xfail(reason="Not implemented yet")
def test_provider_decorator_registers_a_context_manager_decorated_function(
    sut: Registry,
) -> None:
    @sut.provider
    @contextmanager
    def create_fake_service() -> Iterator[FakeService]:
        yield FakeService()

    assert sut[FakeService] == Provider(create_fake_service, enter=True)


@pytest.mark.parametrize(
    "function", [_create_fake_service_iterator, _create_fake_service_generator]
)
def test_provider_decorator_registers_generator_wrapped_as_context_manager(
    sut: Registry, function: Callable[[], Iterator[FakeService]]
) -> None:
    sut.provider(function)

    assert sut[FakeService] == Provider(contextmanager(function))


@use_enter
@use_lifetimes
def test_provider_decorator_registers_a_factory_provider_with_options(
    sut: Registry, enter: bool, lifetime: Lifetime
) -> None:
    sut.provider(lifetime=lifetime, enter=enter)(_create_fake_service_no_params)

    assert sut[FakeService] == Provider(
        _create_fake_service_no_params, lifetime=lifetime, enter=enter
    )
