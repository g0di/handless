from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, _GeneratorContextManager, contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isgeneratorfunction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    Literal,
    ParamSpec,
    TypeVar,
    cast,
)

from typing_extensions import Self

from handless._utils import (
    get_non_variadic_params,
    get_untyped_parameters,
)
from handless.exceptions import RegistrationError

if TYPE_CHECKING:
    from handless import Container

_P = ParamSpec("_P")
_T = TypeVar("_T")


ServiceGetter = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[Any]]
    | Callable[..., AbstractContextManager[_T]]
)
ServiceGetterIn = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[Any]]
    | Callable[..., AbstractContextManager[_T]]
    | Callable[..., Iterator[_T]]
)

Lifetime = Literal["transient", "singleton", "scoped"]

# NOTE: Following functions are factories for building various service descriptors
# The name is capitalized even if it is functions to emphasis on the fact that those
# function are for building objects without any particular side effect just as what
# Pydantic does.


def Alias(service_type: type[_T]) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor.alias(service_type)


def Value(value: _T, *, enter: bool = False) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor.value(value, enter=enter)


def Singleton(
    factory: ServiceGetter[_T], *, enter: bool = True
) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor.factory(factory, lifetime="singleton", enter=enter)


def Scoped(
    factory: ServiceGetter[_T], *, enter: bool = True
) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor.factory(factory, lifetime="scoped", enter=enter)


def Factory(
    factory: ServiceGetter[_T],
    *,
    lifetime: Lifetime = "transient",
    enter: bool = True,
) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor.factory(factory, lifetime=lifetime, enter=enter)


@dataclass(unsafe_hash=True)
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
    def alias(cls, alias_type: type[_T]) -> Self:
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
        )

    def _get_getter_comparator(self) -> object:
        if hasattr(self.getter, "__code__"):
            return self.getter.__code__.co_code
        return self.getter


class Lifetime_(ABC):
    @abstractmethod
    def accept(self, container: "Container", descriptor: ServiceDescriptor[_T]) -> _T:
        pass


class SingletonLifetime(Lifetime_):
    def accept(self, container: "Container", descriptor: ServiceDescriptor[_T]) -> _T:
        return container._resolve_singleton(descriptor)
