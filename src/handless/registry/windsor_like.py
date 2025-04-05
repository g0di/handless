from typing import Any, Callable, Generic, Self, TypeVar

from handless import Provider

_T = TypeVar("_T")


class Component(Generic[_T]):
    def __init__(self, service_type: type[_T]) -> None:
        self.service_type = service_type

    def implemented_by(self, implementation_type: type[_T]) -> Self:
        return self

    def instance(self, instance: _T) -> Self:
        return self

    def use_factory(self, factory: Callable[..., _T]) -> Self:
        return self


class Registry:
    def __init__(self) -> None:
        self._services: dict[type[Any, Provider[Any]]] = {}

    def register(self, *providers: Component[Any]) -> Self:
        for provider in providers:
            self._services[provider.service_type] = provider
        return self


if __name__ == "__main__":
    registry = Registry()
    registry.register(
        Component(str).implemented_by(str),
        Component(int).instance(42),
        Component(bool).use_factory(lambda: True).singleton(),
    )
    print(registry._services)
