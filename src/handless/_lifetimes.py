from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, TypeVar

if TYPE_CHECKING:
    from handless._registrations import Registration
    from handless.containers import Container


_T = TypeVar("_T")


LifetimeLiteral = Literal["transient", "singleton", "scoped"]


class Lifetime(Protocol):
    def accept(self, container: Container, registration: Registration[_T]) -> _T: ...


@dataclass
class Transient(Lifetime):
    def accept(self, container: Container, registration: Registration[_T]) -> _T:
        return container._resolve_transient(registration)  # noqa: SLF001


@dataclass
class Scoped(Lifetime):
    def accept(self, container: Container, registration: Registration[_T]) -> _T:
        return container._resolve_scoped(registration)  # noqa: SLF001


@dataclass
class Singleton(Lifetime):
    def accept(self, container: Container, registration: Registration[_T]) -> _T:
        return container._resolve_singleton(registration)  # noqa: SLF001


# NOTE: no need to create an instance of lifetime each time for the moment
_transient = Transient()
_scoped = Scoped()
_singleton = Singleton()


def parse(lifetime: LifetimeLiteral) -> Lifetime:
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
