import inspect
from contextlib import AbstractContextManager
from dataclasses import dataclass, is_dataclass
from functools import cached_property
from inspect import isclass
from types import LambdaType
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    NewType,
    ParamSpec,
    TypeVar,
    cast,
    get_type_hints,
)

_P = ParamSpec("_P")
_T = TypeVar("_T")

ServiceFactory = Callable[..., _T] | Callable[..., AbstractContextManager[_T]]
Lifetime = Literal["transient", "singleton", "scoped"]


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

    def __post_init__(self) -> None:
        if is_lambda_function(self.factory) and count_func_params(self.factory) > 1:
            raise ValueError("lambda functions can only have 0 or 1 argument")

    @cached_property
    def type_hints(self) -> dict[str, Any]:
        if is_lambda_function(self.factory):
            return {
                pname: inspect.Parameter
                for pname in inspect.signature(self.factory).parameters
            }
        if isinstance(self.factory, NewType):
            return get_type_hints(self.factory.__supertype__.__init__)  # type: ignore[misc]
        if isclass(self.factory):
            return get_type_hints(self.factory.__init__)
        if is_dataclass(self.factory):
            # get type hints on dataclass instance returns constructor type hints instead
            # of __call__ method
            return get_type_hints(self.factory.__call__)
        try:
            return get_type_hints(self.factory)
        except Exception:
            return get_type_hints(self.factory.__call__)  # type: ignore[operator]


# NOTE: Following functions are factories for building various service descriptors
# The name is capitalized even if it is functions to emphasis on the fact that those
# function are for building objects without any particular side effect just as what
# Pydantic does.


def Value(val: _T) -> ValueServiceDescriptor[_T]:
    return ValueServiceDescriptor(val)


def Factory(
    factory: ServiceFactory[_T], lifetime: Lifetime | None = None
) -> FactoryServiceDescriptor[_T]:
    return FactoryServiceDescriptor(factory, lifetime=lifetime or "transient")


def Singleton(factory: ServiceFactory[_T]) -> FactoryServiceDescriptor[_T]:
    return FactoryServiceDescriptor(factory, lifetime="singleton")


def Scoped(factory: ServiceFactory[_T]) -> FactoryServiceDescriptor[_T]:
    return FactoryServiceDescriptor(factory, lifetime="scoped")


def Alias(service_type: type[_T]) -> AliasServiceDescriptor[_T]:
    return AliasServiceDescriptor(service_type)


def get_return_type(func: Callable[..., _T]) -> type[_T]:
    fn_type_hints = get_type_hints(func)
    if "return" not in fn_type_hints:
        raise ValueError(f"Function {func} has no return type annotation")
    return cast(type[_T], get_type_hints(func).get("return"))


def is_dataclass_instance(obj: Any) -> bool:
    return is_dataclass(obj) and not isclass(obj)


def is_lambda_function(value: Any) -> bool:
    return isinstance(value, LambdaType) and value.__name__ == "<lambda>"


def count_func_params(value: Callable[..., Any]) -> int:
    return len(inspect.signature(value).parameters)
