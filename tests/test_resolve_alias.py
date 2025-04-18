from handless import Container, Registry
from tests.helpers import FakeService, IFakeService


def test_register_alias_resolve_the_given_alias(
    registry: Registry, container: Container
) -> None:
    expected = FakeService()
    registry.bind(FakeService).to_value(expected)
    registry.bind(IFakeService).to(FakeService)  # type: ignore[type-abstract]

    received = container.resolve(IFakeService)  # type: ignore[type-abstract]

    assert received is expected
