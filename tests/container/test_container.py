import pytest

from handless import Container, Registry, Scope
from handless.exceptions import RegistrationNotFoundError
from tests.helpers import FakeService


def test_create_scope_returns_a_new_scoped_container(sut: Container) -> None:
    scope1 = sut.create_scope()
    scope2 = sut.create_scope()

    assert isinstance(scope1, Scope)
    assert isinstance(scope2, Scope)
    assert scope1 is not scope2


@pytest.mark.parametrize(
    "sut",
    [Container(Registry()), Container(Registry()).create_scope()],
    ids=["Root container", "Scoped container"],
)
def test_resolve_unregistered_service_type_autobind_a_transient_factory_by_default(
    sut: Container,
) -> None:
    resolved = sut.resolve(FakeService)
    resolved2 = sut.resolve(FakeService)

    assert isinstance(resolved, FakeService)
    assert isinstance(resolved2, FakeService)
    assert resolved is not resolved2


@pytest.mark.parametrize(
    "sut",
    [
        Container(Registry(autobind=False)),
        Container(Registry(autobind=False)).create_scope(),
    ],
    ids=["Strict root container", "Strict scoped container"],
)
def test_resolve_unregistered_service_type_raise_an_error_when_autobind_is_disabled(
    sut: Container,
) -> None:
    with pytest.raises(RegistrationNotFoundError):
        sut.resolve(FakeService)
