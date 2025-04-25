from handless import Binding, Registry
from handless._lifetimes import Singleton
from handless.providers import Value


def test_registry_overrides_registered_bindings(registry: Registry) -> None:
    registry.bind(object).to_value(object())
    with registry.override() as override:
        override.bind(object).to_value(expected := object())
        registration = override.lookup(object)

    assert registration == Binding(
        object, Value(expected), enter=False, lifetime=Singleton()
    )
