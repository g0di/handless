from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from handless._utils import autocontextmanager, compare_functions, get_injectable_params

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless.containers import Container

_T_co = TypeVar("_T_co", covariant=True)


class Provider(ABC, Generic[_T_co]):
    @abstractmethod
    def __call__(self, container: Container) -> _T_co:
        raise NotImplementedError


class Value(Provider[_T_co]):
    def __init__(self, value: _T_co) -> None:
        self._value = value

    def __call__(self, container: Container) -> _T_co:  # noqa: ARG002
        return self._value

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Value) and self._value == value._value

    def __hash__(self) -> int:
        return hash(self._value)


class Factory(Provider[_T_co]):
    if TYPE_CHECKING:
        # NOTE: Overload the constructor to reflect the fact that we autowrap
        # generators into context managers.
        @overload  # type: ignore[no-overload-impl]
        def __new__(
            cls,
            factory: Callable[..., Iterator[_T_co]],
            params: dict[str, type[Any]] | None = ...,
        ) -> Factory[AbstractContextManager[_T_co]]: ...

        @overload
        def __new__(
            cls,
            factory: Callable[..., _T_co],
            params: dict[str, type[Any]] | None = ...,
        ) -> Factory[_T_co]: ...

    def __init__(
        self, factory: Callable[..., _T_co], params: dict[str, type[Any]] | None = None
    ) -> None:
        self._factory = autocontextmanager(factory)
        self._params = get_injectable_params(factory, params)

    def __call__(self, container: Container) -> _T_co:
        args = {p.name: container.resolve(p.annotation) for p in self._params}
        return self._factory(**args)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Factory) and compare_functions(
            self._factory, value._factory
        )


class Dynamic(Provider[_T_co]):
    if TYPE_CHECKING:
        # NOTE: Overload the constructor to reflect the fact that we autowrap
        # generators into context managers.
        @overload  # type: ignore[no-overload-impl]
        def __new__(
            cls, factory: Callable[..., Iterator[_T_co]]
        ) -> Dynamic[AbstractContextManager[_T_co]]: ...

        @overload
        def __new__(cls, factory: Callable[..., _T_co]) -> Dynamic[_T_co]: ...

    def __init__(self, lambda_factory: Callable[[Container], _T_co]) -> None:
        self._lambda_factory = autocontextmanager(lambda_factory)

    def __call__(self, container: Container) -> _T_co:
        return self._lambda_factory(container)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Dynamic) and compare_functions(
            self._lambda_factory, value._lambda_factory
        )


class Alias(Provider[_T_co]):
    def __init__(self, alias_type: type[_T_co]) -> None:
        self._alias_type = alias_type

    def __call__(self, container: Container) -> _T_co:
        return container.resolve(self._alias_type)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Alias) and self._alias_type == value._alias_type
