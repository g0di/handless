import inspect
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from inspect import Parameter
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Literal,
    NewType,
    OrderedDict,
    ParamSpec,
    TypeVar,
)

from handless._utils import (
    count_func_params,
    get_untyped_parameters,
    is_lambda_function,
)
from handless.exceptions import RegistrationError

if TYPE_CHECKING:
    from handless.container import Container

_P = ParamSpec("_P")
_T = TypeVar("_T")

ServiceFactory = Callable[..., _T] | Callable[..., AbstractContextManager[_T]]
Lifetime = Literal["transient", "singleton", "scoped"]


# NOTE: Following functions are factories for building various service descriptors
# The name is capitalized even if it is functions to emphasis on the fact that those
# function are for building objects without any particular side effect just as what
# Pydantic does.


def Value(val: _T, *, enter: bool = False) -> "ValueServiceDescriptor[_T]":
    return ValueServiceDescriptor(val, enter=enter)


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
class ValueServiceDescriptor(ServiceDescriptor[_T]):
    value: _T
    enter: bool = False

    def accept(self, container) -> _T:
        return container._resolve_value(self)


@dataclass(frozen=True)
class AliasServiceDescriptor(ServiceDescriptor[_T]):
    alias: type[_T]

    def accept(self, container) -> _T:
        return container._resolve_alias(self)


@dataclass(frozen=True)
class FactoryServiceDescriptor(ServiceDescriptor[_T]):
    factory: ServiceFactory[_T]
    lifetime: Lifetime = "transient"
    enter: bool = True

    params: OrderedDict[str, Parameter] = field(
        default_factory=OrderedDict, hash=False, init=False
    )

    def __post_init__(self) -> None:
        signature = inspect.signature(
            self.factory.__supertype__
            if isinstance(self.factory, NewType)
            else self.factory,
            eval_str=True,
        )
        params = {
            name: param
            for name, param in signature.parameters.items()
            if param.kind not in {Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD}
        }

        if is_lambda_function(self.factory):
            if count_func_params(self.factory) > 1:
                raise RegistrationError(
                    "Lambda functions can takes up to only one parameter"
                )
        elif empty_params := get_untyped_parameters(params):
            msg = f"Factory {self.factory} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

        self.params.update(params)

    def accept(self, container: "Container") -> _T:
        if self.lifetime == "scoped":
            return container._resolve_scoped(self)
        if self.lifetime == "singleton":
            return container._resolve_singleton(self)
        return container._resolve_transient(self)
