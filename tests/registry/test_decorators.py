import pytest

from handless import Lifetime, Provider, Registry
from tests.helpers import FakeService
from tests.registry.test_register import use_enter, use_lifetimes


@pytest.fixture
def sut() -> Registry:
    return Registry()


def test_provider_decorator_registers_a_factory_provider(sut: Registry) -> None:
    @sut.provider
    def create_fake_service() -> FakeService:
        return FakeService()

    assert sut[FakeService] == Provider(create_fake_service)


@use_enter
@use_lifetimes
def test_provider_decorator_registers_a_factory_provider_with_options(
    sut: Registry, enter: bool, lifetime: Lifetime
) -> None:
    @sut.provider(lifetime=lifetime, enter=enter)
    def create_fake_service() -> FakeService:
        return FakeService()

    assert sut[FakeService] == Provider(
        create_fake_service, lifetime=lifetime, enter=enter
    )
