# handless <!-- omit in toc -->

> :construction: This repository is currently under construction. Its public API might change at any time without notice nor major version bump.

A Python dependency injection container that automatically resolves and injects dependencies without polluting your code with framework-specific decorators. Inspired by [lagom] and [svcs], it keeps your code clean and flexible while offering multiple service registration options. 🚀

> :warning: For the moment, autowiring is not available. It means that you have to use factories for constructing your types. This feature will be released in the future.

- [🔧 What is Dependency Injection, and Why Should You Care?](#-what-is-dependency-injection-and-why-should-you-care)
- [🧱 What is a DI Container?](#-what-is-a-di-container)
- [🚀 What This Library Solves](#-what-this-library-solves)
- [Getting started](#getting-started)
- [Usage](#usage)
  - [Registering types](#registering-types)
  - [Register a value](#register-a-value)
  - [Register a factory](#register-a-factory)
  - [Register an alias](#register-an-alias)
  - [Context managers and cleanups](#context-managers-and-cleanups)
  - [Lifetimes](#lifetimes)
  - [Context local registry](#context-local-registry)
- [Recipes](#recipes)
  - [Registering implementations for protocols and abstract classes](#registering-implementations-for-protocols-and-abstract-classes)
  - [Choosing dependencies at runtime](#choosing-dependencies-at-runtime)
  - [Use with FastAPI](#use-with-fastapi)
- [Q\&A](#qa)
  - [Why requiring having a context object to resolve types instead of using the container directly?](#why-requiring-having-a-context-object-to-resolve-types-instead-of-using-the-container-directly)
  - [Why using a fluent API to register types as a two step process?](#why-using-a-fluent-api-to-register-types-as-a-two-step-process)
  - [Why using objects for lifetimes? (Why not using enums or literals?)](#why-using-objects-for-lifetimes-why-not-using-enums-or-literals)
- [Contributing](#contributing)

## 🔧 What is Dependency Injection, and Why Should You Care?

In modern software design, **dependency injection (DI)** is a technique where a component’s dependencies are **provided from the outside**, rather than hard-coded inside it. This leads to:

- ✅ More modular and testable code
- ✅ Easier substitution of dependencies (e.g., mocks, stubs, alternative implementations)
- ✅ Clearer separation of concerns

**Example without DI:**

```python
class Service:
    def __init__(self):
        self.db = Database()  # tightly coupled
```

**Example with DI:**

```python
class Service:
    def __init__(self, db: Database):
        self.db = db  # dependency injected
```

---

## 🧱 What is a DI Container?

As your project grows, wiring up dependencies manually becomes tedious and error-prone.

A **DI container** automates this by:

- 🔍 Scanning constructor signatures or factory functions
- 🔗 Resolving and injecting required dependencies
- ♻️ Managing object lifetimes (singleton, transient, scoped...)
- 🧹 Handling cleanup for context-managed resources

Instead of writing all the wiring logic yourself, the container does it for you — predictably and declaratively.

---

## 🚀 What This Library Solves

This library provides a lightweight, flexible **dependency injection container for Python** that helps you:

- ✅ **Register** services with factories, providers, or values
- ✅ **Resolve** dependencies automatically (~~with type hints~~ or custom logic)
- ✅ **Manage lifecycles** — including context-aware caching and cleanup
- ✅ **Control instantiation** via explicit contexts, ensuring predictability

It’s designed to be **explicit, minimal, and intuitive** — avoiding magic while saving you boilerplate.

## Getting started

Install it through you preferred packages manager:

```shell
pip install handless
```

Once installed, you can create a container allowing you to specify how to resolve your types and start resolving them.

```python
from handless import Container


class Cat:
    def __init__(self, name: str) -> None:
        self.name = name

    def meow(self) -> None:
        print(f"{self.name}: Meow!")


container = Container()
container.register(str).use_value("Kitty")
container.register(Cat).use_factory(lambda ctx: Cat(ctx.resolve(str)))

with container.open_context() as ctx:
    foo = ctx.resolve(Cat)
    foo.meow()
    # Kitty: Meow!

container.release()
```

## Usage

### Registering types

To resolve types from your container, you must first create one and register them on it. There should be only one container per application. The container should be released when your application shutdown (or your tests ends).

> :bulb: The container should be placed on your application composition root. This can be as simple as a `bootstrap.py` file on your package root.

> :warning: The container is the most "high level" component of your application. It can import anything from any sub modules. However, none of your code should depends on the container itself. Otherwise you're going to use the service locator anti-pattern. There can be exceptions to this rule, for example, when used in an HTTP API controllers (as suggested in `svcs`). The most important thing is that your services and objects should not use the container directly in order to pull its dependencies on the fly.

```python
import random
import atexit

from handless import Container

container = Container()
container.register(str).use_value("Hello Container!")
container.register(int).use_factory(lamba: random.randint(0, 10))

# If your application has not shutdown callback you can use atexit
# to release the container on program exit
atexit.register(container.release)

# You can also use the container with a context manager.
# This can be useful during tests
with Container() as container:
    container.register(str).use_value("Hello Container!")
    container.register(int).use_factory(lamba: random.randint(0, 10))
```

### Register a value

You can register a value directly for your type. When resolved, the provided value will be returned as-is.

```python
from handless import Container


class Foo:
    pass

foo = Foo()
container = Container()
container.register(Foo).use_value(foo)

with container.open_context() as ctx:
    resolved_foo = ctx.resolve(Foo)
    assert resolved_foo is foo
```

### Register a factory

> :construction: Under construction

### Register an alias

> :construction: Under construction

### Context managers and cleanups

> :construction: Under construction

### Lifetimes

> :construction: Under construction

### Context local registry

> :construction: Under construction

## Recipes

### Registering implementations for protocols and abstract classes

> :construction: Under construction

### Choosing dependencies at runtime

> :construction: Under construction

### Use with FastAPI

> :construction: Under construction

## Q&A

### Why requiring having a context object to resolve types instead of using the container directly?

- Separation of concerns
- Simpler API
- Transient dependencies captivity
- Everything is a context
- Easier management and release of resolved values

### Why using a fluent API to register types as a two step process?

- type hints limitations

### Why using objects for lifetimes? (Why not using enums or literals?)

- Allow creating its own lifetimes
- Allows to add options in the future
- Avoid if statements

## Contributing

Running tests: `uv run pytest tests --cov --cov-report=term-missing`

[lagom]: https://lagom-di.readthedocs.io
[svcs]: https://svcs.hynek.me/
