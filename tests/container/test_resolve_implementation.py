from handless import Container, Registry
from tests.helpers import FakeService, IFakeService


def test_resolve_an_implementation_descriptor_resolves_the_actual_implementation_type() -> (
    None
):
    sut: Container = (
        Registry()
        .register_singleton(FakeService, value := FakeService())
        .register_implementation(IFakeService, FakeService)
        .create_container()
    )

    resolved1 = sut.resolve(IFakeService)  # type: ignore[type-abstract]

    assert resolved1 is value
