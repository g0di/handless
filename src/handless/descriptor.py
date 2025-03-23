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
    OrderedDict,
    ParamSpec,
    TypeVar,
)

from handless._utils import (
    count_func_params,
    get_non_variadic_params,
    get_untyped_parameters,
    is_lambda_function,
)
from handless.exceptions import RegistrationError

if TYPE_CHECKING:
    from handless.container import Container

_P = ParamSpec("_P")
_T = TypeVar("_T")

ServiceFactory = (
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


def Value(val: _T, *, enter: bool = False) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(lambda: val, enter=enter, lifetime="singleton")


def Factory(
    factory: ServiceFactory[_T],
    *,
    lifetime: Lifetime = "transient",
    enter: bool = True,
) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime=lifetime, enter=enter)


def Singleton(
    factory: ServiceFactory[_T], *, enter: bool = True
) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime="singleton", enter=enter)


def Scoped(
    factory: ServiceFactory[_T], *, enter: bool = True
) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime="scoped", enter=enter)


def Alias(service_type: type[_T]) -> "AliasServiceDescriptor[_T]":
    return AliasServiceDescriptor(service_type)


class ServiceDescriptor(ABC, Generic[_T]):
    @abstractmethod
    def accept(self, container: "Container") -> _T:
        raise NotImplementedError


@dataclass(frozen=True)
class AliasServiceDescriptor(ServiceDescriptor[_T]):
    alias: type[_T]

    def accept(self, container: "Container") -> _T:
        return container._resolve_alias(self)


@dataclass(unsafe_hash=True)
class FactoryServiceDescriptor(ServiceDescriptor[_T]):
    factory: ServiceFactory[_T]
    lifetime: Lifetime = "transient"
    enter: bool = True
    params: OrderedDict[str, Parameter] = field(
        default_factory=OrderedDict, hash=False, init=False
    )

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, FactoryServiceDescriptor)
            and self._get_factory_code() == value._get_factory_code()
            and self.lifetime == value.lifetime
            and self.enter == value.enter
        )

    def _get_factory_code(self) -> object:
        if hasattr(self.factory, "__code__"):
            return self.factory.__code__.co_code
        return self.factory

    def __post_init__(self) -> None:
        if isgeneratorfunction(self.factory):
            self.factory = contextmanager(self.factory)
        # NOTE: we omit variadic params because we don't know how to autowire them yet
        params = get_non_variadic_params(self.factory)

        if is_lambda_function(self.factory):
            # NOTE: for lambda function we allow 0 arguments or a single one which will
            # the container itself
            if count_func_params(self.factory) > 1:
                raise RegistrationError(
                    "Lambda functions can takes up to only one parameter"
                )
        elif empty_params := get_untyped_parameters(params):
            # NOTE: if some parameters are missing type annotation we cannot autowire
            msg = f"Factory {self.factory} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

        self.params.update(params)

    def accept(self, container: "Container") -> _T:
        if self.lifetime == "scoped":
            return container._resolve_scoped(self)
        if self.lifetime == "singleton":
            return container._resolve_singleton(self)
        return container._resolve_transient(self)
