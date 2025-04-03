import logging
from inspect import isclass, isfunction
from typing import Any, Callable, Iterator, TypeVar, overload

from typing_extensions import ParamSpec, Self

from handless import Lifetime
from handless._container import Container
from handless._descriptor import ServiceDescriptor, ServiceDescriptorFactoryIn
from handless._utils import get_return_type

_P = ParamSpec("_P")
_T = TypeVar("_T")


class Registry:
    """Central registry describing how to resolve services.

    You may have at most one registry per entrypoint in your application. The registry should
    live as long as your application does and be instantiated in your composition root.

    :param strict: If `False` the registry will always returns a default transient
        service descriptor for unregistered type, None otherwise.
    """

    def __init__(self, strict: bool = False) -> None:
        self._strict = strict
        self._services: dict[type, ServiceDescriptor[Any]] = {}
        self._logger = logging.getLogger(__name__)

    def __contains__(self, key: object) -> bool:
        return key in self._services

    def __getitem__(self, key: type[_T]) -> ServiceDescriptor[_T]:
        return self._services[key]

    def __delitem__(self, key: type[Any]) -> None:
        del self._services[key]

    def __iter__(self) -> Iterator[type[Any]]:
        return iter(self._services)

    def __len__(self) -> int:
        return len(self._services)

    def __setitem__(self, key: type[_T], descriptor: ServiceDescriptor[_T]) -> None:
        self._services[key] = descriptor
        self._logger.info("Registered %s: %s", key, descriptor)

    @overload
    def get(self, type_: type[_T]) -> ServiceDescriptor[_T] | None: ...

    @overload
    def get(self, type_: type[Any]) -> ServiceDescriptor[Any] | None: ...

    def get(self, type_: type[_T]) -> ServiceDescriptor[_T] | None:
        """Get descriptor registered for given type, if any.

        :param type_: Service type or `None`
        :return: Descriptor registered for this type or `None` if `strict` is `True`.
        """
        descriptor = self._services.get(type_)
        if descriptor is None and not self._strict:
            return ServiceDescriptor(type_)
        return descriptor

    def create_container(self) -> Container:
        """Create a container using this registry.

        :return: Created container
        """
        return Container(self)

    def register(self, type_: type[_T], descriptor: ServiceDescriptor[_T]) -> Self:
        """Register given descriptor for given type.

        :param type_: Service type
        :param descriptor: Service descriptor
        :return: The registry
        """
        self._services[type_] = descriptor
        return self

    def register_factory(
        self,
        type_: type[_T],
        factory: ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        lifetime: Lifetime = "transient",
        enter: bool = True,
    ) -> Self:
        """Register a factory for given type.

        A factory descriptor calls given factory and returns its value each time it get
        resolved. This behavior can be adapted depending on the provided lifetime.

        :param type_: Service type
        :param factory: Callable returning instances of given type.
            If `None` the type itself will be used. Defaults to None.
        :param lifetime: Service instances lifetime. Defaults to "transient".
        :param enter: Whether or not to enter context managers if returned by given factory.
        :return: The registry
        """
        return self.register(
            type_,
            ServiceDescriptor.for_factory(
                factory or type_, lifetime=lifetime, enter=enter
            ),
        )

    def register_singleton(
        self,
        type_: type[_T],
        singleton: _T | ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        enter: bool | None = None,
    ) -> Self:
        """Register a singleton for given type.

        A singleton descriptor always resolves with the exact same value for a container
        lifetime. When a callable is given, it will executed only once requested and its
        result cached.

        :param type_: Service type
        :param singleton: An instance of given type, a class or function returning an
            instance of given type or `None`. If `None`, defaults to given type.
        :param enter: Whether or not to enter context managers. Defaults to `True` for
            singleton classes and functions, `False` for instances.
        :return: The registry
        """
        singleton = singleton or type_

        if isclass(singleton) or isfunction(singleton):  # noqa: F821
            return self.register(
                type_,
                ServiceDescriptor.for_factory(
                    singleton or type_,
                    enter=True if enter is None else enter,
                    lifetime="singleton",
                ),
            )
        return self.register(
            type_,
            ServiceDescriptor.for_instance(
                singleton, enter=False if enter is None else enter
            ),
        )

    def register_scoped(
        self,
        type_: type[_T],
        factory: ServiceDescriptorFactoryIn[_T] | None = None,
        *,
        enter: bool = True,
    ) -> Self:
        """Register a scoped factory for given type.

        A scoped descriptor always resolves with the exact same value for a container
        scope lifetime. Given callable will be executed once requested and its result
        cached per container scope.

        :param type_: Service type
        :param factory: A class or function returning an instance of given type or `None`.
            If `None`, defaults to given type_.
        :param enter: Whether or not to enter context managers. Defaults to `True`.
        :return: The registry
        """
        return self.register(
            type_,
            ServiceDescriptor.for_factory(
                factory or type_, enter=enter, lifetime="scoped"
            ),
        )

    def register_implementation(
        self, type_: type[_T], implementation_type: type[_T]
    ) -> Self:
        """Register an implementation for given type.

        An implementation descriptor acts as an alias. When given type will be resolved
        the specified implementation type will be resolved instead.

        :param type_: Service type
        :param alias: Implementing class
        :return: The registry
        """
        return self.register(
            type_, ServiceDescriptor.for_implementation(implementation_type)
        )

    @overload
    def factory(
        self, *, lifetime: Lifetime = ...
    ) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def factory(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def factory(
        self,
        factory: Callable[_P, _T] | None = None,
        *,
        lifetime: Lifetime = "transient",
    ) -> Any:
        """Decorate a function registered as a factory service descriptor for its return type annotation.

        Decorator parenthesis can be omitted.

        :param factory: Decorated function, defaults to None
        :param lifetime: Descriptor lifetime, defaults to "transient"
        :return: The pristine decorated function
        """

        def wrapper(factory: Callable[_P, _T]) -> Callable[_P, _T]:
            rettype = get_return_type(factory)
            if not rettype:
                raise ValueError(f"{factory} has no return type annotation")
            self.register_factory(rettype, factory, lifetime=lifetime)
            # NOTE: return decorated func untouched to ease reuse
            return factory

        if factory is not None:
            return wrapper(factory)
        return wrapper

    # Singleton decorator

    @overload
    def singleton(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def singleton(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def singleton(self, factory: Callable[_P, _T] | None = None) -> Any:
        """Decorate a function registered as a singleton service descriptor for its return type annotation.

        Decorator parenthesis can be omitted.

        :param factory: Decorated function, defaults to None
        :return: The pristine decorated function
        """
        return self.factory(factory, lifetime="singleton")  # type: ignore[call-overload]

    # Scoped decorator

    @overload
    def scoped(self) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...

    @overload
    def scoped(self, factory: Callable[_P, _T]) -> Callable[_P, _T]: ...

    def scoped(self, factory: Callable[_P, _T] | None = None) -> Any:
        """Decorate a function registered as a scoped service descriptor for its return type annotation.

        Decorator parenthesis can be omitted.

        :param factory: Decorated function, defaults to None
        :return: The pristine decorated function
        """
        return self.factory(factory, lifetime="scoped")  # type: ignore[call-overload]
