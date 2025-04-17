from handless import Registry
from tests.helpers import FakeService, IFakeService


def test_resolve_type_with_alias_binding_resolves_the_alias_instead() -> None:
    registry = Registry()

    registry.bind(FakeService).to_value(value := FakeService())
    registry.bind(IFakeService).to(FakeService)  # type: ignore[type-abstract]

    sut = registry.create_container()

    resolved1 = sut.resolve(IFakeService)  # type: ignore[type-abstract]

    assert resolved1 is value
