from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from handless.registry import Registry

_T = TypeVar("_T")


class ServiceBinder(Generic[_T]):
    def __init__(self, registry: Registry, type_: type[_T]):
        self._registry = registry
        self._type = type_

    def to_self(self) -> None:
        self._registry.register(self._type)

    def to_value(self, value: _T) -> None:
        self._registry.register_value(self._type, value)
