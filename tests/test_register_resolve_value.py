from typing import Callable, Generic, NewType, Protocol, TypedDict, TypeVar

import pytest
from typing_extensions import Self, Unpack

from handless import Container, Registry, Value


class ServiceProtocol(Protocol): ...


class Service(ServiceProtocol):
    def __init__(self):
        self.entered = False
        self.exited = False

    def __enter__(self) -> Self:
        self.entered = True
        return self

    def __exit__(self, *args: object) -> None:
        self.exited = True


ServiceAlias = NewType("ServiceAlias", Service)


ContainerFactory = Callable[[Registry], Container]


def create_container(registry: Registry) -> Container:
    return registry.create_container()


def create_scoped_container(registry: Registry) -> Container:
    return create_container(registry).create_scope()


_T = TypeVar("_T", contravariant=True)

TypeResolver = Callable[[Container, type[_T]], _T]


def resolve_type(container: Container, service_type: type[_T]) -> _T:
    return container.resolve(service_type)


def get_type(container: Container, service_type: type[_T]) -> _T:
    return container[service_type]


class ValueRegistererOptions(TypedDict, total=False):
    enter: bool


class TypeRegisterer(Protocol, Generic[_T]):
    def __call__(
        self,
        registry: Registry,
        type_: type[_T],
        value: _T,
        **kwargs: Unpack[ValueRegistererOptions],
    ) -> None: ...


def register_explicit_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueRegistererOptions],
) -> None:
    registry.register_value(service_type, value, **kwargs)


def register_implicit_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueRegistererOptions],
) -> None:
    registry.register(service_type, value)


def register_implicit_value_descriptor(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueRegistererOptions],
) -> None:
    registry.register(service_type, Value(value, **kwargs))


def set_value(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueRegistererOptions],
) -> None:
    registry[service_type] = value


def set_value_descriptor(
    registry: Registry,
    service_type: type[_T],
    value: _T,
    **kwargs: Unpack[ValueRegistererOptions],
) -> None:
    registry[service_type] = Value(value, **kwargs)


@pytest.mark.parametrize(
    "register",
    [
        register_explicit_value,
        register_implicit_value,
        register_implicit_value_descriptor,
        set_value,
        set_value_descriptor,
    ],
)
@pytest.mark.parametrize("resolve", [resolve_type, get_type])
@pytest.mark.parametrize(
    "create_container", [create_container, create_scoped_container]
)
@pytest.mark.parametrize("service_type", [ServiceProtocol, Service, ServiceAlias])
class TestRegisterResolveValue:
    def test_register_resolve_value_resolves_with_that_value(
        self,
        register: TypeRegisterer[ServiceProtocol | Service | ServiceAlias],
        resolve: TypeResolver[ServiceProtocol | Service | ServiceAlias],
        create_container: ContainerFactory,
        service_type: type[ServiceProtocol] | type[Service] | type[ServiceAlias],
    ) -> None:
        registry = Registry()
        expected = Service()
        register(registry, service_type, expected)
        sut = create_container(registry)

        received1 = resolve(sut, service_type)
        received2 = resolve(sut, service_type)

        assert received1 is received2 is expected

    @pytest.mark.parametrize("options", [{}, {"enter": False}])
    def test_resolve_context_manager_value_is_not_entered(
        self,
        register: TypeRegisterer[ServiceProtocol | Service | ServiceAlias],
        resolve: TypeResolver[ServiceProtocol | Service | ServiceAlias],
        create_container: ContainerFactory,
        service_type: type[ServiceProtocol] | type[Service] | type[ServiceAlias],
        options: ValueRegistererOptions,
    ) -> None:
        registry = Registry()
        expected = Service()
        register(registry, service_type, expected, **options)
        sut = create_container(registry)

        resolve(sut, service_type)

        assert not expected.entered
