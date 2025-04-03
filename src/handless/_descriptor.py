from contextlib import AbstractContextManager, _GeneratorContextManager, contextmanager
from dataclasses import dataclass, field
from inspect import Parameter, isgeneratorfunction
from typing import Any, Callable, Generic, Iterator, Literal, TypeVar, cast

from typing_extensions import Self

from handless._utils import get_non_variadic_params, get_untyped_parameters

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
"""Service lifetime.
`transient`: descriptor's factory is called every time the service is resolved.
`singleton`: descriptor's factory is called and cached a single time per container.
`scoped`: descriptor's factory is called and cached a single time per scoped container.
"""


@dataclass(unsafe_hash=True, slots=True)
class ServiceDescriptor(Generic[_T]):
    """Describe how to resolve a service.

    You should prefer to use class methods to create instances of this class rather than
    the constructor directly.
    """

    factory: ServiceDescriptorFactory[_T]
    """Callable returning an instance of the described service."""
    lifetime: Lifetime = "transient"
    """Determines *when* the `factory` should be called by containers."""
    enter: bool = True
    """Whether or not to enter `factory` returned objects context manager, if any."""
    params: tuple[Parameter, ...] = field(default_factory=tuple)
    """`factory` parameters. If provided, it will be merged into ones extracted from its signature.

    You may want to provide this if you want to override the type of a parameter,
    in particular if its missing type annotation.
    """

    @classmethod
    def for_factory(
        cls,
        factory: ServiceDescriptorFactoryIn[_T],
        lifetime: Lifetime = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Self:
        """Create a factory service descriptor.

        If `factory` is a generator function, it will be wrapped in a context manager
        automatically.

        If `params` is provided, it will override the parameters extracted from `factory` signature.
        :param factory: A callable returning an instance of the described service.
        :param lifetime: The lifetime of the service.
        :param enter: Whether or not to enter the context manager returned by `factory`, if any.
        :param params: A dictionary of parameters to override the ones extracted from `factory` signature.
        :return: A service descriptor.
        """
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
        """Create an instance service desciptor.

        This creates a singleton service descriptor which will always returns the given
        value.
        """
        return cls.for_factory(lambda: instance, lifetime="singleton", enter=enter)

    @classmethod
    def for_implementation(cls, implementation_type: type[_T]) -> Self:
        """Create an implementation service descriptor.

        This create a service descriptor which will be resolved by actually resolving
        the given implementation type.

        :param alias_type: _description_
        :return: _description_
        """
        return cls.for_factory(
            lambda x: x, enter=False, params={"x": implementation_type}
        )

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
            raise ValueError(msg)

        self.params = tuple(params.values())

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ServiceDescriptor)
            and self._get_comparable_factory() == value._get_comparable_factory()
            and self.lifetime == value.lifetime
            and self.enter == value.enter
            and self.params == value.params
        )

    def _get_comparable_factory(self) -> object:
        if hasattr(self.factory, "__code__"):
            return self.factory.__code__.co_code
        return self.factory
