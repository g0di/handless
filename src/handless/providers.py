from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from handless._utils import autocontextmanager, compare_functions, get_injectable_params

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

    from handless.containers import Container

_T_co = TypeVar("_T_co", covariant=True)


class Provider(Generic[_T_co]):
    if TYPE_CHECKING:
        # NOTE: Overload the constructor to reflect the fact that we autowrap
        # generators into context managers.
        @overload  # type: ignore[no-overload-impl]
        def __new__(
            cls,
            factory: Callable[..., Iterator[_T_co]],
            params: dict[str, type[Any]] | None = ...,
        ) -> Provider[AbstractContextManager[_T_co]]: ...

        @overload
        def __new__(
            cls,
            factory: Callable[..., _T_co],
            params: dict[str, type[Any]] | None = ...,
        ) -> Provider[_T_co]: ...

    def __init__(
        self, factory: Callable[..., _T_co], params: dict[str, type[Any]] | None = None
    ) -> None:
        self._factory = autocontextmanager(factory)
        self._params = get_injectable_params(factory, overrides=params)

    def __call__(self, container: Container) -> _T_co:
        args = {p.name: container.get(p.annotation) for p in self._params}
        return self._factory(**args)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Provider)
            and compare_functions(self._factory, value._factory)
            and self._params == value._params
        )
