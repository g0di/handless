from containers.registry import Registry
from containers import descriptors 


class Foo:
    pass


def foo_factory() -> Foo:
    yield Foo()


Registry()
    .register(FactoryServiceDescriptor(Foo, foo_factory))
    .register_factory(Foo, foo_factory)
    .register_singleton(Foo, foo_factory)
    .register_scoped(Foo, foo_factory)

registry = Registry()
registry[IFoo] = Foo
registry[IFoo] = descriptors.as_singleton(Foo)
registry[IFoo] = descriptors.as_scoped(Foo)



registry[Foo]