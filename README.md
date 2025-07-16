# handless <!-- omit in toc -->

> :construction: This repository is currently under construction. Its public API might change at any time without notice nor major version bump.

A Python dependency injection container that automatically resolves and injects dependencies without polluting your code with framework-specific decorators. Inspired by [lagom] and [svcs], it keeps your code clean and flexible while offering multiple service registration options. 🚀

- [🔧 What is Dependency Injection, and Why Should You Care?](#-what-is-dependency-injection-and-why-should-you-care)
- [🧱 What is a DI Container?](#-what-is-a-di-container)
- [🚀 What This Library Solves](#-what-this-library-solves)
- [Getting started](#getting-started)
- [Core](#core)
  - [Containers](#containers)
    - [Register a value](#register-a-value)
    - [Register a factory](#register-a-factory)
      - [Use the given type as its own factory](#use-the-given-type-as-its-own-factory)
  - [Register an alias](#register-an-alias)
  - [Lifetimes](#lifetimes)
  - [Context managers and cleanups](#context-managers-and-cleanups)
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

- ✅ **Register** services with factories, values or aliases
- ✅ **Resolve** dependencies automatically (with type hints or custom logic)
- ✅ **Manage lifecycles** — including context-aware caching and cleanup (singleton, transient, contextual)
- ✅ **Control instantiation** via explicit contexts, ensuring predictability

It’s designed to be **explicit, minimal, and intuitive** — avoiding magic while saving you boilerplate.

## Getting started

Install it through you preferred packages manager:

```shell
pip install handless
```

Once installed, you can create a container allowing you to specify how to resolve your types and start resolving them. Here is an example showcasing most features of the container.

```python
import smtplib
from dataclasses import dataclass
from typing import Protocol

from handless import Container, Contextual, ResolutionContext, Singleton, Transient


@dataclass
class User:
    email: str


@dataclass
class Config:
    smtp_host: str


class UserRepository(Protocol):
    def add(self, cat: User) -> None: ...
    def get(self, email: str) -> User | None: ...


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self._users: list[User] = []

    def add(self, user: User) -> None:
        self._users.append(user)

    def get(self, email: str) -> User | None:
        for user in self._users:
            if user.email == email:
                return user
        return None


class NotificationManager(Protocol):
    def send(self, user: User, message: str) -> None: ...


class StdoutNotificationManager(NotificationManager):
    def send(self, user: User, message: str) -> None:
        print(f"{user.email} - {message}")  # noqa: T201


class EmailNotificationManager(NotificationManager):
    def __init__(self, smtp: smtplib.SMTP) -> None:
        self.server = smtp
        self.server.noop()

    def send(self, user: User, message: str) -> None:
        msg = f"Subject: My Service notification\n{message}"
        self.server.sendmail(
            from_addr="myservice@example.com", to_addrs=[user.email], msg=msg
        )


class UserService:
    def __init__(
        self, users: UserRepository, notifications: NotificationManager
    ) -> None:
        self.users = users
        self.notifications = notifications

    def create_user(self, email: str) -> None:
        user = User(email)
        self.users.add(user)
        self.notifications.send(user, "Your account has been created")

    def get_user(self, email: str) -> User:
        user = self.users.get(email)
        if not user:
            msg = f"There is no user with email {email}"
            raise ValueError(msg)
        return user


config = Config(smtp_host="stdout")

container = Container()
container.register(Config).value(config)

# User repository
container.register(InMemoryUserRepository).self(lifetime=Singleton())
container.register(UserRepository).alias(InMemoryUserRepository)  # type: ignore[type-abstract]

# Notification manager
container.register(smtplib.SMTP).factory(
    lambda ctx: smtplib.SMTP(ctx.resolve(Config).smtp_host)),
    lifetime=Singleton(),
    enter=True,
)
container.register(StdoutNotificationManager).self(lifetime=Transient())
container.register(EmailNotificationManager).self()


@container.factory
def create_notification_manager(
    config: Config, ctx: ResolutionContext
) -> NotificationManager:
    if config.smtp_host == "stdout":
        return ctx.resolve(StdoutNotificationManager)
    return ctx.resolve(EmailNotificationManager)


# Top level service
container.register(UserService).self(lifetime=Contextual())


with container.open_context() as ctx:
    service = ctx.resolve(UserService)
    service.create_user("hello.world@handless.io")
    # hello.world@handless.io - Your account has been created
    print(service.get_user("hello.world@handless.io"))  # noqa: T201
    # User(email='hello.world@handless.io')  # noqa: ERA001


container.release()
```

## Core

### Containers

Containers allows to register types and specify how to resolve them (get an instance of this type). Each registered type get a factory function attached depending on how you registered it.

There should be at most one container per entrypoint in your application (a CLI, a HTTP server, ...). You can share the same container for all your entrypoints. A test is considered as an entrypoint as well.

> :bulb: The container should be placed on your application composition root. This can be as simple as a `bootstrap.py` file on your package root.

> :warning The container is the most "high level" component of your application. It can import anything from any sub modules. However, none of your code should depends on the container itself. Otherwise you're going to use the service locator anti-pattern. There can be exceptions to this rule, for example, when used in an HTTP API controllers (as suggested in `svcs`).

#### Register a value

You can register a value directly for your type. When resolved, the provided value will be returned as-is.

```python
from handless import Container


class Foo:
    pass

foo = Foo()
container = Container()
container.register(Foo).value(foo)
resolved_foo = container.open_context().resolve(Foo)
assert resolved_foo is foo
```

#### Register a factory

If you want the container to create instances of your types for you you can instead register a factory. A factory is a callable taking no or several arguments and returning an instance of the type registered. The callable can be a lambda function, a regular function or even a type (a class). When resolved, the container will take care of calling the factory and return its return value. If your factory takes arguments, the container will first resolve its arguments using their type annotations and pass them to the factory.

> :warning: your callable arguments must have type annotation to be properly resolved. If missing, an error will be raised at registration time.

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
    self.bar = bar

def create_foo(bar: int) -> Foo:
    return Foo(bar)

container = Container()
container.register(int).value(42)
container.register(Foo).factory(create_foo)
resolved_foo = container.open_context().resolve(Foo)

assert isinstance(resolved_foo, Foo)
assert resolved_foo.bar == 42
```

##### Use the given type as its own factory

When you want to register a type and use it as its own factory, you can use the `self()` method instead. The previous example can be simplified as following:

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
    self.bar = bar

container = Container()
container.register(int).value(42)
container.register(Foo).self()
resolved_foo = container.open_context().resolve(Foo)

assert isinstance(resolved_foo, Foo)
assert resolved_foo.bar == 42
```

### Register an alias

> :construction: Under construction

### Lifetimes

> :construction: Under construction

### Context managers and cleanups

If your application has no shutdown mechanism you can register your container `release` method using `atexit` module to release on program exit.

```python
import atexit

from handless import Container

container = Container()
container.register(str).value("hello world!")

# hello world!
atexit.register(container.release)
```

Releasing the container is idempotent and can be used several times. Each time, all singletons will be cleared and then context manager exited, if any.

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

Running tests: `uv run nox`

[lagom]: https://lagom-di.readthedocs.io
[svcs]: https://svcs.hynek.me/
