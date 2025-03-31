from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeVar

if TYPE_CHECKING:
    from handless._container import Container
    from handless._descriptor import ServiceDescriptor

_T = TypeVar("_T")


Lifetime = Literal["transient", "singleton", "scoped"]


class ServiceLifetime(ABC):
    @abstractmethod
    def resolve(
        self, container: "Container", descriptor: ServiceDescriptor[_T]
    ) -> _T: ...

    @classmethod
    def from_string(cls, lifetime: Lifetime) -> ServiceLifetime:
        match lifetime:
            case "scoped":
                return Scoped()
            case "transient":
                return Transient()
            case "singleton":
                return Transient()


@dataclass
class Transient(ServiceLifetime):
    def resolve(self, container: "Container", descriptor: ServiceDescriptor[_T]) -> _T:
        return container._resolve_transient(descriptor)


@dataclass
class Singleton(ServiceLifetime):
    def resolve(self, container: "Container", descriptor: ServiceDescriptor[_T]) -> _T:
        return container._resolve_singleton(descriptor)


@dataclass
class Scoped(ServiceLifetime):
    def resolve(self, container: "Container", descriptor: ServiceDescriptor[_T]) -> _T:
        return container._resolve_scoped(descriptor)
