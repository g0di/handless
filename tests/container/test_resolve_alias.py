from unittest.mock import Mock

from handless import Alias, Container, Registry
from tests.helpers import FakeService, IFakeService


def test_resolve_an_alias_descriptor_resolves_the_actual_alias() -> None:
    factory = Mock(FakeService)
    sut: Container = (
        Registry()  # type:ignore[misc]
        .register_factory(FakeService, factory)
        .register(IFakeService, Alias(FakeService))
        .create_container()
    )

    resolved1 = sut.resolve(IFakeService)

    assert resolved1 is factory.return_value
    factory.assert_called_once()
