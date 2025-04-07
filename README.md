# handless <!-- omit in toc -->

> :construction: This repository is currently under construction. Its public API might change at any time without notice nor major version bump.

A Python dependency injection container that automatically resolves and injects dependencies without polluting your code with framework-specific decorators. Inspired by [lagom] and [svcs], it keeps your code clean and flexible while offering multiple service registration options. 🚀

- [Getting started](#getting-started)
- [Naming](#naming)
  - [Registry](#registry)
  - [Provider](#provider)
  - [Factory](#factory)
  - [Container](#container)
  - [Scoped Container](#scoped-container)
  - [Lifetime](#lifetime)
- [Usage](#usage)
  - [Register an object](#register-an-object)
    - [Context managers](#context-managers)
  - [Register a factory](#register-a-factory)
    - [Default factory](#default-factory)
      - [Autowiring](#autowiring)
    - [Manual factory](#manual-factory)
    - [Decorator](#decorator)
  - [Register an alias](#register-an-alias)
- [Recipes](#recipes)
- [Q\&A](#qa)
  - [Why separate registry and container? Why not use the container to register types?](#why-separate-registry-and-container-why-not-use-the-container-to-register-types)
  - [Why providing a single `register` function to register various kind of providers instead of having many more explicit ones?](#why-providing-a-single-register-function-to-register-various-kind-of-providers-instead-of-having-many-more-explicit-ones)
- [Contributing](#contributing)

## Getting started

Install through you preferred packages manager:

```shell
pip install handless
```

Once installed, you can create a registry allowing you to specify how to resolve your types.

```python
from handless import Registry


class Cat:
    def meow(self) -> None:
        print("Meow!")

registry = Registry().register(Foo, Foo())

with registry.create_container() as c:
    foo = c.resolve(Foo)
    foo.meow()
    # Meow!
```

## Naming

This part present the various components involved in this library.

> :bulb: If you're already familiar with dependency injection you might skip this section.

> :warning: Dependency injection and its concepts are subject to interpretation. The following definitions apply to this library but may differ to other dependencu injection frameworks which could opt for different naming conventions.

### Registry

A registry is an object mapping types to providers. It basically tells containers how to get an instance for a given type. There should up to one registry per entrypoint in an application (if you have a HTTP API and a CLI you may have one registry for each). However, you can share the same registry for all your entrypoints if possible.

### Provider

A provider is an object defining how to get an instance of a given type. It holds the function allowing to get instance of a type as well as other options like its lifetime (i.e: when the container should get a new instance or prefer a cached one) and whether or not enter context managers when returned by its function.

### Factory

A factory is a function or a type which produces object of a particular type. It is bound to a provider.

### Container

A container is an object allowing to resolve types in order to get an instance of it. It holds a reference on a registry that he uses to know how to resolve requested types. There should be one container per application living for the same duration. The container keeps a cache of created objects depending on their lifetime and also retains entered context managers. When closed, the container exits all its entered context manager and clear its cache.

### Scoped Container

It is a container which lifetime is bound to a specific scope. There can be many scoped container during the whole application lifetime. As an example, scoped container are created per request, for a HTTP API, or per message for an event/message handler. It is up to you to define your scope(s) and create a scoped container when necessary.

### Lifetime

Lifetime are tied to providers. It indicates to a container when it should call a provider's factory in order to get an instance of the registered type. There is three lifetimes at the moment:

- _transient_ (default): Provide's factory is called on each resolve.
- _scoped_: Provide's factory is called once per scoped container.
- _singleton_: Provide's factory is called once per container.

> :warning: Lifetimes only dictate to containers WHEN to call a provider's factory or use cached object. It means that if you specify a _transient_ lifetime with a factory which actually always returns the same object, you'll end up with a _singleton_. The container do not check in any way for returned objects are always uniques.

## Usage

There is several ways to register your types in the registry which are described in the following sections.

### Register an object

You can register a plain object directly for your type. When resolved, the container will give you back the original object.

```python
from handless import Registry


class Foo:
  pass

foo = Foo()
registry = Registry().register(Foo, foo)
resolved_foo = registry.create_container().resolve(Foo)

assert resolved_foo is foo
```

> :information_source: This is also known as a singleton.

#### Context managers

By default registered objects being context managers are not entered automatically by the registry. You can however, tells
the registry to do so by passing the `enter=True` argument.

```python
from handless import Registry


class Foo:
    def __enter__(self):
      self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True
        pass

registry = Registry().register(Foo, Foo(), enter=True)

with registry.create_container() as container:
    foo = container.resolve(Foo)

    assert foo.entered

assert foo.exited
```

> :information_source: Context managers are exited automatically when the container is closed.

> :warning: Additional arguments are ignored. If provided a warning will be raised.

### Register a factory

If you want your objects to be constructed dynamically you can pass either `None` or a function to the register method.

#### Default factory

When passing passing `None` (or omitting the argument) to the register function, the container will use the type itself to produces objects of that type.

> :bulb: By default, you do not have to register your types this way. The registry will automatically use the given type as factory if not registered. This is known as _autobiding_. You can disable this behavior by setting the `autobind` argument to `False` on your registry: `Registry(autobind=False)`.

```python
from handless import Registry

class Foo:
    pass

# With autobind
foo = Registry().create_container().resolve(Foo)
assert isinstance(foo, Foo)

# Without autobinding
container = Registry(autobind=False).register(Foo)
container = registry.create_container()
foo = container.resolve(Foo)
assert isinstance(foo, Foo)
```

##### Autowiring

When you register a type which has arguments, the container will resolve then inject them into the type constructor.
This is also known as _autowiring_.

```python
from handless import Registry


class Bar:
    pass

class Foo:
    def __init__(self, bar: Bar) -> None:
      self.bar = bar

bar = Bar()
registry = Registry()
container = registry.create_container()
foo = container.resolve(Foo)
assert foo.bar is bar
```

> :warning: Type constructor arguments must all be typed in order to work properly. If not, a `TypeError` will be raised at registration.

#### Manual factory

If it's not possible to autowire your type or you want to introduce custom logic you can pass instead a function returning an instance of given type. This function can takes up to one argument, being the container itself, allowing you to resolve other types as well.

> :bulb: This can be particularly useful for types taking primitive types as parameters like `str`, `int`, ...

```python
from handless import Registry


class Bar:
    def __init__(self, value: str) -> None:
      self.value = value

class Foo:
    def __init__(self, bar: Bar) -> None:
      self.bar = bar

registry = (Registry()
    .register(Bar, lambda: Bar("Hello World!"))
    .register(Foo, lambda c: Foo(c.resolve(Bar)))
)
container = registry.create_container()
foo = container.resolve(Foo)
assert foo.bar.value == "Hello World!"
```

#### Decorator

Lastly, you can register a function as factory for a type by decorating it. The decorated function can takes any resolvable parameters, including a `handless.Container`. Those parameters will be resolved and injected at runtime by the container when called. The return type annotation of the decorated function will be used as the registered type.

> :warning: Omitting return type annotation will raise an `TypeError`.

```python
from handless import Registry


class Bar:
    def __init__(self, value: str) -> None:
        self.value = value

class Foo:
    def __init__(self, bar: Bar)

registry = Registry()


@registry.provider
def get_foo(bar: Bar) -> Foo:
    return Foo(bar)
```

### Register an alias

Finally, you can register a type alias. It means that resolving your type will end up resolving the provided alias instead.
This is particularly useful for registering implementation types against abstracts or protocols.

```python
from handless import Registry

class IFoo(Protocol):
    # Works as well with ABC
    pass


class Foo:
    pass

registry = Registry().register(IFoo, Foo)

with registry.create_container() as container:
    foo = container.resolve(IFoo)

    assert isinstance(foo, Foo)
```

> :warning: When `autobind` is disabled the alias itself must be registered as well or the registry will raise exception when trying to resolve your type.

> :warning: Additional arguments are ignored. If provided a warning will be raised.

## Recipes

> :construction: _Under construction_

## Q&A

> :warning: The following answers are subjective.

### Why separate registry and container? Why not use the container to register types?

This better separate concerns. A registry is supposed to register how to resolve your types. A container is supposed to resolve your types. Once your registry is setup and your container created, you're not supposed to register types while your application is running. This can lead to harder debugging and weird behaviors. Instead of raising errors at runtime when trying to register types in a running container, I preferred to split into two distinct objects so you can not even register on the container.

### Why providing a single `register` function to register various kind of providers instead of having many more explicit ones?

This one is mostly due to Python typing system. I wanted this library to be fully typed in order to prevent from registering wrong providers to types upfront.
To better understand why I did not split registration into several functions, look at the following example

```python
from typing import TypeVar


_T = TypeVar("_T")

def register_value(type: type[_T], value: _T) -> None:
    ...

register_value(str, 42) # No mypy issues
```

If you give this to mypy, you'll get no typing errors. This is because the `_T` variable is not bound to any particular type so this example is perfectly fine. Mypy will infer that `_T` as `str | int`.

The other solution would have been to somehow prebind the `_T` type but this would have incurred a more complex API.

> :bulb: This behavior is actually the same as in some other languages.

## Contributing

Running tests: `uv run pytest tests --cov=containers --cov-report=term-missing`

[lagom]: https://lagom-di.readthedocs.io
[svcs]: https://svcs.hynek.me/
