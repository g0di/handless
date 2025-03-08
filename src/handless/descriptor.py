import inspect
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from inspect import Parameter
from types import LambdaType
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    NewType,
    OrderedDict,
    ParamSpec,
    TypeVar,
)

from handless.exceptions import RegistrationError

_P = ParamSpec("_P")
_T = TypeVar("_T")

ServiceFactory = Callable[..., _T] | Callable[..., AbstractContextManager[_T]]
Lifetime = Literal["transient", "singleton", "scoped"]


# NOTE: Following functions are factories for building various service descriptors
# The name is capitalized even if it is functions to emphasis on the fact that those
# function are for building objects without any particular side effect just as what
# Pydantic does.


def Value(val: _T) -> "ValueServiceDescriptor[_T]":
    return ValueServiceDescriptor(val)


def Factory(
    factory: ServiceFactory[_T], lifetime: Lifetime | None = None
) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime=lifetime or "transient")


def Singleton(factory: ServiceFactory[_T]) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime="singleton")


def Scoped(factory: ServiceFactory[_T]) -> "FactoryServiceDescriptor[_T]":
    return FactoryServiceDescriptor(factory, lifetime="scoped")


def Alias(service_type: type[_T]) -> "AliasServiceDescriptor[_T]":
    return AliasServiceDescriptor(service_type)


class ServiceDescriptor(Generic[_T]):
    # NOTE: using a real class instead of types union to allow using instance checks
    pass


@dataclass(frozen=True)
class ValueServiceDescriptor(ServiceDescriptor[_T]):
    value: _T


@dataclass(frozen=True)
class AliasServiceDescriptor(ServiceDescriptor[_T]):
    alias: type[_T]


@dataclass(frozen=True)
class FactoryServiceDescriptor(ServiceDescriptor[_T]):
    factory: ServiceFactory[_T]
    lifetime: Lifetime = "transient"
    params: OrderedDict[str, Parameter] = field(default_factory=OrderedDict, hash=False)

    def __post_init__(self) -> None:
        params = inspect.signature(
            self.factory.__supertype__
            if isinstance(self.factory, NewType)
            else self.factory,
            eval_str=True,
        ).parameters

        if _is_lambda_function(self.factory):
            if _count_func_params(self.factory) > 1:
                raise RegistrationError(
                    "Lambda functions can takes up to only one parameter"
                )
        elif empty_params := get_untyped_parameters(dict(params)):
            msg = f"Factory {self.factory} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

        self.params.update(params)


def _is_lambda_function(value: Any) -> bool:
    return isinstance(value, LambdaType) and value.__name__ == "<lambda>"


def get_untyped_parameters(params: dict[str, Parameter]) -> list[str]:
    return [
        pname for pname, param in params.items() if param.annotation is Parameter.empty
    ]


def _count_func_params(value: Callable[..., Any]) -> int:
    return len(inspect.signature(value).parameters)
