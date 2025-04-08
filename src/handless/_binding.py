from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, ParamSpec, TypeVar

from handless import _provider
from handless._lifetime import BaseLifetime, TransientLifetime

if TYPE_CHECKING:
    from handless._container import Container  # noqa: F401

_T = TypeVar("_T")
_P = ParamSpec("_P")


@dataclass(slots=True)
class Binding(Generic[_T]):
    type_: type[_T]
    provider: _provider.Provider[_T]
    lifetime: BaseLifetime = field(default_factory=TransientLifetime)
    enter: bool = True
