from handless import Container, Registry
from tests.helpers import FakeService, IFakeService


def test_resolve_type_with_alias_binding_resolves_the_alias_instead() -> None:
    sut: Container = (
        Registry()
        .register(FakeService, value := FakeService())
        .register(IFakeService, FakeService)  # type: ignore[type-abstract]
        .create_container()
    )

    resolved1 = sut.resolve(IFakeService)  # type: ignore[type-abstract]

    assert resolved1 is value
