from typing import Any, Callable, Generic, NewType, TypeVar

from typing_extensions import Self

from handless import Provider

_T = TypeVar("_T")


class Binder(Generic[_T]):
    def __init__(self, registry: "Registry", service_type: type[_T]) -> None:
        self.registry = registry
        self.service_type = service_type

    def to(self, implementation_type: type[_T]) -> Self:
        return self

    def to_self(self) -> Self:
        return self

    def to_value(self, value: _T) -> Self:
        return self

    def to_factory(self, factory: Callable[..., _T]) -> Self:
        return self


class Registry:
    def __init__(self) -> None:
        self._services: dict[type[Any, Provider[Any]]] = {}

    def bind(self, service_type: type[_T]) -> Binder[_T]:
        return Binder(self, service_type)


MyBool = NewType("MyBool", bool)


if __name__ == "__main__":
    registry = Registry()
    registry.bind(str).to_self()
    registry.bind(MyBool).to_self().as_singleton()
    registry.bind(bool).to(MyBool)
    registry.bind(object).to_value(object())
    registry.bind(object).to_factory(lambda: object())
