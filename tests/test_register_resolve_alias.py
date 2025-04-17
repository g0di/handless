from unittest.mock import Mock

from handless import Container, Registry


class FakeService:
    pass


def test_register_alias_resolve_the_given_alias(
    registry: Registry, container: Container
) -> None:
    fake_service_factory = Mock(wraps=lambda: FakeService())
    registry.bind(FakeService).to_factory(fake_service_factory)
    registry.bind(object).to(FakeService)

    received = container.resolve(object)

    assert isinstance(received, FakeService)
    fake_service_factory.assert_called_once()
