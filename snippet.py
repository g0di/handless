from typing import Any

from snippet import Registry


class IFoo:
    pass


class Foo(IFoo):
    pass


def Singleton(any: Any) -> Any:
    pass


registry = Registry()
registry[IFoo] = Foo
registry[IFoo] = Singleton(Foo)
registry[IFoo] = Factory(Foo, lifetime="scoped")
registry[IFoo] = Scoped(Foo)
registry[IFoo] = Alias(Foo)
registry[IFoo] = Value(Foo())


registry = Registry()
registry[IFoo] = Foo
registry[IFoo] = as_singleton(Foo)
registry[IFoo] = as_factory(Foo, lifetime="scoped")
registry[IFoo] = as_scoped(Foo)
registry[IFoo] = as_alias(Foo)
registry[IFoo] = as_value(Foo())
