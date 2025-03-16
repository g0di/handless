from handless import Registry
from handless.descriptor import ValueServiceDescriptor
from tests.helpers import FakeService, use_enter


def test_register_explicit_value(sut: Registry) -> None:
    value = FakeService()
    ret = sut.register_value(FakeService, value)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == ValueServiceDescriptor(value, enter=False)


@use_enter
def test_register_explicit_value_with_options(sut: Registry, enter: bool) -> None:
    value = FakeService()
    ret = sut.register_value(FakeService, value, enter=enter)

    assert ret is sut
    assert sut.get_descriptor(FakeService) == ValueServiceDescriptor(value, enter=enter)
