import pytest

from handless import Binding, Registry
from handless._lifetime import SingletonLifetime
from handless._provider import ValueProvider


@pytest.mark.xfail(reason="Not implemented")
def test_registry_overrides_registered_bindings(sut: Registry) -> None:
    sut.register(object, object())
    sut.overrides.register(object, expected := object())  # type: ignore[attr-defined]

    binding = sut.lookup(object)

    assert binding == Binding(
        object, ValueProvider(expected), enter=False, lifetime=SingletonLifetime()
    )
