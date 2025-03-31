from contextlib import AbstractContextManager, _GeneratorContextManager, contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isgeneratorfunction
from typing import Any, Callable, Generic, Iterator, Literal, TypeVar, cast

from typing_extensions import Self

from handless._utils import get_non_variadic_params, get_untyped_parameters
from handless.exceptions import RegistrationError

_T = TypeVar("_T")


ServiceGetter = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[_T]]
    | Callable[..., AbstractContextManager[_T]]
)
ServiceGetterIn = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[Any]]
    | Callable[..., AbstractContextManager[_T]]
    | Callable[..., Iterator[_T]]
)

Lifetime = Literal["transient", "singleton", "scoped"]


@dataclass(unsafe_hash=True, slots=True)
class ServiceDescriptor(Generic[_T]):
    """Describe how to resolve a service."""

    getter: ServiceGetter[_T]
    """Callable that returns an instance of the service."""
    lifetime: Lifetime = "transient"
    """Service instance lifetime."""
    enter: bool = True
    """Whether or not to enter servcice instance context manager, if any."""
    params: dict[str, Parameter] = field(default_factory=dict, hash=False)
    """Service getter parameters types merged with given ones, if any."""

    @classmethod
    def factory(
        cls,
        getter: ServiceGetterIn[_T],
        lifetime: Lifetime = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Self:
        if isgeneratorfunction(getter):
            getter = contextmanager(getter)
        actual_params = {
            p: Parameter(p, Parameter.POSITIONAL_OR_KEYWORD, annotation=ptype)
            for p, ptype in (params or {}).items()
        }
        return cls(
            cast(ServiceGetter[_T], getter),
            lifetime=lifetime,
            enter=enter,
            params=actual_params,
        )

    @classmethod
    def value(cls, value: _T, enter: bool = False) -> Self:
        return cls.factory(lambda: value, lifetime="singleton", enter=enter)

    @classmethod
    def implementation(cls, alias_type: type[_T]) -> Self:
        return cls.factory(lambda x: x, enter=False, params={"x": alias_type})

    def __post_init__(self) -> None:
        # Merge given callable inspected params with provided ones.
        # NOTE: we omit variadic params because we don't know how to autowire them yet
        self.params = get_non_variadic_params(self.getter) | self.params

        if empty_params := get_untyped_parameters(self.params):
            # NOTE: if some parameters are missing type annotation we cannot autowire
            msg = f"Factory {self.getter} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ServiceDescriptor)
            and self._get_getter_comparator() == value._get_getter_comparator()
            and self.lifetime == value.lifetime
            and self.enter == value.enter
            and self.params == value.params
        )

    def _get_getter_comparator(self) -> object:
        if hasattr(self.getter, "__code__"):
            return self.getter.__code__.co_code
        return self.getter
