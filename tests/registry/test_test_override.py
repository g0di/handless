from handless import Registration, Registry
from handless._lifetimes import Singleton
from handless.providers import Value


def test_registry_overrides_registered_bindings(sut: Registry) -> None:
    sut.register(object).value(object())
    with sut.override() as registry:
        registry.register(object).value(expected := object())
        registration = sut.lookup(object)

    assert registration == Registration(
        object, Value(expected), enter=False, lifetime=Singleton()
    )
