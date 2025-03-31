from unittest.mock import create_autospec

from handless import Registry
from handless._descriptor import ServiceDescriptor
from tests.helpers import FakeService


def test_register_service_descriptor(sut: Registry) -> None:
    descriptor = create_autospec(ServiceDescriptor)
    ret = sut.register(FakeService, descriptor)

    assert ret is sut
    assert sut.get(FakeService) is descriptor


def test_set_service_descriptor_registers_it(sut: Registry) -> None:
    descriptor = create_autospec(ServiceDescriptor)
    sut[FakeService] = descriptor

    assert sut.get(FakeService) is descriptor
