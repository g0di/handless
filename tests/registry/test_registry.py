import pytest

from handless import Binding, Registry


@pytest.mark.xfail(reason="Not implemented")
def test_registry_overrides_registered_bindings(registry: Registry) -> None:
    registry.bind(object).to_value(object())
    with registry.override() as override:
        override.bind(object).to_value(expected := object())
        registration = override.lookup(object)

    assert registration == Binding(
        object, lambda: expected, enter=False, lifetime="singleton"
    )
