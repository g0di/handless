from contextlib import AbstractContextManager, contextmanager
from typing import Any, Callable, Iterator

import pytest
from typing_extensions import Self

from handless import Lifetime, Registry
from tests.test_descriptors import use_lifetimes


class FakeServiceWithContextManager(AbstractContextManager):
    def __init__(self):
        self.entered = False

    def __enter__(self) -> Self:
        self.entered = True
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        self.exited = True


def fake_factory_returning_context_manager() -> FakeServiceWithContextManager:
    return FakeServiceWithContextManager()


@contextmanager
def fake_factory_returning_iterator() -> Iterator[FakeServiceWithContextManager]:
    srv = FakeServiceWithContextManager()
    try:
        yield srv
    finally:
        pass


# Use cases
# Registering a type which is context manager (has enter and exit method)
# Registering a factory function which returns a value which is a context manager
# Registering a factory function which is decorated with @contextmanager decorator


@pytest.mark.parametrize(
    "factory", [FakeServiceWithContextManager, fake_factory_returning_context_manager]
)
@use_lifetimes
def test_resolve_a_context_manager_enter_its_context(
    factory: Callable[..., FakeServiceWithContextManager], lifetime: Lifetime
):
    container = (
        Registry()
        .register_factory(FakeServiceWithContextManager, factory, lifetime=lifetime)
        .create_container()
        .create_scope()
    )

    resolved = container.resolve(FakeServiceWithContextManager)

    assert resolved.entered
