from handless import Alias, Registry
from tests.helpers import FakeService, IFakeService


def test_register_explicit_alias(sut: Registry) -> None:
    ret = sut.register_alias(IFakeService, FakeService)

    assert ret is sut
    assert sut.get_descriptor(IFakeService) == Alias(FakeService)
