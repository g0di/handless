from handless import Registry, ServiceDescriptor
from tests.helpers import FakeService, IFakeService


def test_register_implementation(sut: Registry) -> None:
    ret = sut.register_implementation(IFakeService, FakeService)

    assert ret is sut
    assert sut.get(IFakeService) == ServiceDescriptor.for_implementation(FakeService)  # type: ignore[type-abstract]
