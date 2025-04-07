from typing import Any, Callable, Generic, Self, TypeVar, get_args

from handless import Provider

_T = TypeVar("_T")


class Registry:
    def __init__(self) -> None:
        self._services: dict[type[Any], Provider[Any]] = {}

    def register(self, *providers: Provider[Any]) -> Self:
        for provider in providers:
            self._services[get_args(provider)[0]] = provider
        return self


if __name__ == "__main__":
    registry = Registry()
    registry.register(
        a := Provider[int].for_alias(str),
        Provider.for_value(42),
        Provider.for_factory(lambda: True),
    )
    print(registry._services)

_U = TypeVar("_U")


class Foo(Generic[_U]):
    def __init__(self, factory: _U) -> None:
        self.factory = factory


def foo(type_: type[_U], value: Callable[[str], _U] | Callable[..., _U]) -> None:
    pass
