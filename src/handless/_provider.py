from contextlib import AbstractContextManager
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    Protocol,
    TypeVar,
    overload,
    runtime_checkable,
)

from handless._utils import autocontextmanager, compare_functions, get_injectable_params

if TYPE_CHECKING:
    from handless._container import Container

_T = TypeVar("_T", covariant=True)


@runtime_checkable
class Provider(Protocol, Generic[_T]):
    def __call__(self, container: "Container") -> _T: ...


class ValueProvider(Provider[_T]):
    def __init__(self, value: _T) -> None:
        self._value = value

    def __call__(self, container: "Container") -> _T:
        return self._value

    def __eq__(self, value: Any) -> bool:
        return isinstance(value, ValueProvider) and self._value == value._value

    def __hash__(self) -> int:
        return hash(self._value)


class FactoryProvider(Provider[_T]):
    if TYPE_CHECKING:
        # NOTE: Overload the constructor to reflect the fact that we autowrap
        # generators into context managers.
        @overload  # type: ignore[no-overload-impl]
        def __new__(
            self,
            factory: Callable[..., Iterator[_T]],
            params: dict[str, type[Any]] | None = ...,
        ) -> "FactoryProvider[AbstractContextManager[_T]]": ...

        @overload
        def __new__(
            self, factory: Callable[..., _T], params: dict[str, type[Any]] | None = ...
        ) -> "FactoryProvider[_T]": ...

    def __init__(
        self, factory: Callable[..., _T], params: dict[str, type[Any]] | None = None
    ) -> None:
        self._factory = autocontextmanager(factory)
        self._params = get_injectable_params(factory, params)

    def __call__(self, container: "Container") -> _T:
        args = {p.name: container.resolve(p.annotation) for p in self._params}
        return self._factory(**args)

    def __eq__(self, value: Any) -> bool:
        return isinstance(value, FactoryProvider) and compare_functions(
            self._factory, value._factory
        )


class LambdaProvider(Provider[_T]):
    if TYPE_CHECKING:
        # NOTE: Overload the constructor to reflect the fact that we autowrap
        # generators into context managers.
        @overload  # type: ignore[no-overload-impl]
        def __new__(
            self, factory: Callable[..., Iterator[_T]]
        ) -> "LambdaProvider[AbstractContextManager[_T]]": ...

        @overload
        def __new__(self, factory: Callable[..., _T]) -> "LambdaProvider[_T]": ...

    def __init__(self, lambda_factory: Callable[["Container"], _T]) -> None:
        self._lambda_factory = autocontextmanager(lambda_factory)

    def __call__(self, container: "Container") -> _T:
        return self._lambda_factory(container)

    def __eq__(self, value: Any) -> bool:
        return isinstance(value, LambdaProvider) and compare_functions(
            self._lambda_factory, value._lambda_factory
        )


class AliasProvider(Provider[_T]):
    def __init__(self, alias_type: type[_T]) -> None:
        self._alias_type = alias_type

    def __call__(self, container: "Container") -> _T:
        return container.resolve(self._alias_type)

    def __eq__(self, value: Any) -> bool:
        return (
            isinstance(value, AliasProvider) and self._alias_type == value._alias_type
        )
