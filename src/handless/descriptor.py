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
    pass

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


def Alias(service_type: type[_T]) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor(implementation=service_type)


def Value(val: _T, *, enter: bool = False) -> "ServiceDescriptor[_T]":
    return Singleton(lambda: val, enter=enter)


def Singleton(
    factory: ServiceFactory[_T], *, enter: bool = True
) -> "ServiceDescriptor[_T]":
    return Factory(factory, lifetime="singleton", enter=enter)


def Scoped(
    factory: ServiceFactory[_T], *, enter: bool = True
) -> "ServiceDescriptor[_T]":
    return Factory(factory, lifetime="scoped", enter=enter)


def Factory(
    factory: ServiceFactory[_T],
    *,
    lifetime: Lifetime = "transient",
    enter: bool = True,
) -> "ServiceDescriptor[_T]":
    return ServiceDescriptor(factory=factory, lifetime=lifetime, enter=enter)


@dataclass(unsafe_hash=True)
class ServiceDescriptor(Generic[_T]):
    factory: ServiceFactory[_T] | None = None
    implementation: type[_T] | None = None
    lifetime: Lifetime = "transient"
    enter: bool = True
    params: OrderedDict[str, Parameter] = field(
        default_factory=OrderedDict, hash=False, init=False
    )

    def __post_init__(self) -> None:
        if self.factory is None:
            return
        if isgeneratorfunction(self.factory):
            self.factory = contextmanager(self.factory)

        # NOTE: we omit variadic params because we don't know how to autowire them yet
        params = get_non_variadic_params(self.factory)

        if is_lambda_function(self.factory):
            # NOTE: for lambda function we allow 0 arguments or a single one (the container itself)
            if count_func_params(self.factory) > 1:
                raise RegistrationError(
                    "Lambda functions can takes up to only one parameter"
                )
        elif empty_params := get_untyped_parameters(params):
            # NOTE: if some parameters are missing type annotation we cannot autowire
            msg = f"Factory {self.factory} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

        self.params.update(params)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ServiceDescriptor)
            and self._get_comparable_factory() == value._get_comparable_factory()
            and self.implementation == value.implementation
            and self.lifetime == value.lifetime
            and self.enter == value.enter
        )

    def _get_comparable_factory(self) -> object:
        if self.factory is None:
            return None
        if hasattr(self.factory, "__code__"):
            return self.factory.__code__.co_code
        return self.factory
