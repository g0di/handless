from handless import Binding, Registry
from handless._lifetimes import Singleton
from handless.providers import Value


def test_registry_overrides_registered_bindings(sut: Registry) -> None:
    sut.bind(object).to_value(object())
    with sut.override() as registry:
        registry.bind(object).to_value(expected := object())
        registration = sut.lookup(object)

    assert registration == Binding(
        object, Value(expected), enter=False, lifetime=Singleton()
    )
