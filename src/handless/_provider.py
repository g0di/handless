import inspect
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

from handless._utils import get_non_variadic_params, get_untyped_parameters

if TYPE_CHECKING:
    from handless._container import Container  # noqa: F401

_T = TypeVar("_T")
_P = ParamSpec("_P")

ProviderFactoryIn = (
    Callable[_P, _T]
    | Callable[_P, AbstractContextManager[_T]]
    | Callable[_P, _GeneratorContextManager[Any, Any, Any]]
    | Callable[_P, Iterator[_T]]
)
ProviderFactory = (
    Callable[_P, _T]
    | Callable[_P, AbstractContextManager[_T]]
    | Callable[_P, _GeneratorContextManager[Any, Any, Any]]
)
ProviderLambdaFactory = ProviderFactoryIn[["Container"], _T] | ProviderFactoryIn[[], _T]
Lifetime = Literal["transient", "singleton", "scoped"]
"""Provider lifetime. Determines when container should call provider's factory to get a value."""


@dataclass(unsafe_hash=True, slots=True)
class Provider(Generic[_T]):
    """Describe how to resolve a type.

    You might not want to use this class constructor directly. Instead prefer using one of
    `for_factory`, `for_value` or `for_alias` class methods.
    """

    factory: ProviderFactory[..., _T]
    """Factory that returns an instance of the descibed type."""
    lifetime: Lifetime = "transient"
    """Provider factory returned values lifetime."""
    enter: bool = True
    """Whether or not to enter `factory` returned objects context manager, if any."""
    params: tuple[Parameter, ...] = field(default_factory=tuple)
    """`factory` parameters. If provided, it will be merged into ones extracted from its signature."""

    @classmethod
    def for_factory(
        cls,
        factory: ProviderFactoryIn[..., _T],
        lifetime: Lifetime = "transient",
        enter: bool = True,
        params: dict[str, type[Any]] | None = None,
    ) -> Self:
        """Create a provider which resolves with value returned by given factory.

        Provided function can have parameters. If so, it must have type annotations. If not,
        annotations can be passed using the `params` argument. The container will first
        resolve the parameters before calling the function with them.

        If the given function is a generator, it will be automatically wrapped into
        a context manager.

        :param factory: Function or type to call to resolve the service. If it has parameters
            if must have type annotations.
        :param lifetime: Lifetime of the values returned by the function, defaults to "transient"
        :param enter: Whether or not to enter context manager if returned by the function, defaults to True
        :param params: Function parameters type annotations override, defaults to None
        :raises TypeError: If the function has parameters without type annotations.
        :return: A factory provider
        """
        if isgeneratorfunction(factory):
            factory = contextmanager(factory)
        actual_params = tuple(
            Parameter(p, Parameter.POSITIONAL_OR_KEYWORD, annotation=ptype)
            for p, ptype in (params or {}).items()
        )
        return cls(
            cast(ProviderFactory[..., _T], factory),
            lifetime=lifetime,
            enter=enter,
            params=actual_params,
        )

    @classmethod
    def for_lambda_factory(
        cls,
        lambda_factory: ProviderLambdaFactory[_T],
        enter: bool = True,
        lifetime: Lifetime = "transient",
    ) -> Self:
        """Same as `for_factory` but for lambda function eventually taking a container as first parameter."""
        try:
            param = next(iter(inspect.signature(lambda_factory).parameters))
            from handless._container import Container

            params = {param: Container}
        except StopIteration:
            params = None

        return cls.for_factory(
            lambda_factory, enter=enter, lifetime=lifetime, params=params
        )

    @classmethod
    def for_value(cls, value: _T, enter: bool = False) -> Self:
        """Creates a provider which always resolves with given value.

        Shorthand for `return cls.for_factory(lambda: value, lifetime="singleton", enter=enter)`

        :param value: The value
        :param enter: Whether or not enter given value context manager, if any, defaults to False
        :return: A value provider
        """
        return cls.for_factory(lambda: value, lifetime="singleton", enter=enter)

    @classmethod
    def for_alias(cls, alias_type: type[_T]) -> Self:
        """Creates a provider which resolves with value resolved for given type.

        Shorthand for `return cls.for_factory(lambda x: x, enter=False, params={"x": alias_type})`

        :param alias_type: Alias type
        :return: An alias provider
        """
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
            raise TypeError(msg)

        self.params = tuple(params.values())

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Provider)
            and self._get_comparable_factory() == value._get_comparable_factory()
            and self.lifetime == value.lifetime
            and self.enter == value.enter
            and self.params == value.params
        )

    def _get_comparable_factory(self) -> object:
        if hasattr(self.factory, "__code__"):
            return self.factory.__code__.co_code
        return self.factory
