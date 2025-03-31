from contextlib import AbstractContextManager, _GeneratorContextManager, contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isgeneratorfunction
from typing import Any, Callable, Generic, Iterator, Literal, TypeVar, cast

from typing_extensions import Self

from handless._utils import get_non_variadic_params, get_untyped_parameters
from handless.exceptions import RegistrationError

_T = TypeVar("_T")


ServiceDescriptorFactory = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[_T]]
    | Callable[..., AbstractContextManager[_T]]
)
ServiceDescriptorFactoryIn = (
    Callable[..., _T]
    | Callable[..., _GeneratorContextManager[Any]]
    | Callable[..., AbstractContextManager[_T]]
    | Callable[..., Iterator[_T]]
)

Lifetime = Literal["transient", "singleton", "scoped"]


@dataclass(unsafe_hash=True, slots=True)
class ServiceDescriptor(Generic[_T]):
    """Describe how to resolve a service."""

    factory: ServiceDescriptorFactory[_T]
    """Factory that returns an instance of the descibed service."""
    lifetime: Lifetime = "transient"
    """Service instance lifetime."""
    enter: bool = True
    """Whether or not to enter `factory` returned objects context manager, if any."""
    params: tuple[Parameter, ...] = field(default_factory=tuple)
    """`factory` parameters. If provided, it will be merged into ones extracted from its signature."""

    @classmethod
    def for_factory(
        cls,
        factory: ServiceDescriptorFactoryIn[_T],
        lifetime: Lifetime = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Self:
        if isgeneratorfunction(factory):
            factory = contextmanager(factory)
        actual_params = tuple(
            Parameter(p, Parameter.POSITIONAL_OR_KEYWORD, annotation=ptype)
            for p, ptype in (params or {}).items()
        )
        return cls(
            cast(ServiceDescriptorFactory[_T], factory),
            lifetime=lifetime,
            enter=enter,
            params=actual_params,
        )

    @classmethod
    def for_instance(cls, instance: _T, enter: bool = False) -> Self:
        return cls.for_factory(lambda: instance, lifetime="singleton", enter=enter)

    @classmethod
    def for_implementation(cls, alias_type: type[_T]) -> Self:
        return cls.for_factory(lambda x: x, enter=False, params={"x": alias_type})

    def __post_init__(self) -> None:
        # Merge given callable inspected params with provided ones.
        # NOTE: we omit variadic params because we don't know how to autowire them yet
        params = get_non_variadic_params(self.factory)
        for override in self.params:
            params[override.name] = params[override.name].replace(
                annotation=override.annotation
            )

        if empty_params := get_untyped_parameters(params):
            # NOTE: if some parameters are missing type annotation we cannot autowire
            msg = f"Factory {self.factory} is missing types for following parameters: {', '.join(empty_params)}"
            raise RegistrationError(msg)

        self.params = tuple(params.values())

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ServiceDescriptor)
            and self._get_getter_comparator() == value._get_getter_comparator()
            and self.lifetime == value.lifetime
            and self.enter == value.enter
            and self.params == value.params
        )

    def _get_getter_comparator(self) -> object:
        if hasattr(self.factory, "__code__"):
            return self.factory.__code__.co_code
        return self.factory
