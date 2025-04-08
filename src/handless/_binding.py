from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

from handless._lifetime import BaseLifetime, TransientLifetime

if TYPE_CHECKING:
    from handless import _provider

_T = TypeVar("_T")


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: _provider.Provider[_T]
    lifetime: BaseLifetime = field(default_factory=TransientLifetime)
    enter: bool = True
