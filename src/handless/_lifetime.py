from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from handless._binding import Binding
    from handless._container import Container


_T = TypeVar("_T")


Lifetime = Literal["transient", "singleton", "scoped"]


class BaseLifetime(Protocol):
    def accept(self, container: Container, binding: Binding[_T]) -> _T: ...


@dataclass
class TransientLifetime(BaseLifetime):
    def accept(self, container: Container, binding: Binding[_T]) -> _T:
        return container._resolve_transient(binding)  # noqa: SLF001


@dataclass
class ScopedLifetime(BaseLifetime):
    def accept(self, container: Container, binding: Binding[_T]) -> _T:
        return container._resolve_scoped(binding)  # noqa: SLF001


@dataclass
class SingletonLifetime(BaseLifetime):
    def accept(self, container: Container, binding: Binding[_T]) -> _T:
        return container._resolve_singleton(binding)  # noqa: SLF001


# NOTE: no need to create an instance of lifetime each time for the moment
_transient = TransientLifetime()
_scoped = ScopedLifetime()
_singleton = SingletonLifetime()


def parse(lifetime: Lifetime) -> BaseLifetime:
    match lifetime:
        case "transient":
            return _transient
        case "singleton":
            return _singleton
        case "scoped":
            return _scoped
        case _:
            msg = f"Invalid lifetime: {lifetime}"
            raise ValueError(msg)
