from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

from handless._lifetime import Lifetime, Transient

if TYPE_CHECKING:
    from handless import _provider
    from handless._container import Container

_T = TypeVar("_T")


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: _provider.Provider[_T]
    lifetime: Lifetime = field(default_factory=Transient)
    enter: bool = True

    def resolve(self, container: Container) -> _T:
        return self.lifetime.accept(container, self)
