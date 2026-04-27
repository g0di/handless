<!-- begin logo -->

<p align="center">
  <a href="https://github.com/hynek/svcs/">
    <img src="handless.logo.png" width="35%" alt="handless logo showing a person doing bycicle without his hands" />
  </a>
</p>

<p align="center">
  <em>Dependency injection without hands in Python.</em>
</p>

<!-- end logo -->

______________________________________________________________________

Handless is a Python dependency injection container which aims at facilitating creation of your objects and services without polluting your code with framework specific code.

In particular it contains the following features:

- 🔌 **Autowiring**: _Handless_ reads your objects constructor to determines its dependencies and resolve them automatically for you without explicit binding
- ♻️ **Lifetimes**: _Handless_ allows you to pick between singleton, scoped, and transient lifetimes to determines when to reuse cached object or get new ones
- 🧹 **Context managers**: _Handless_ automatically enter and exit context managers of your objects without having you to manage them
- 🔁 **Inversion of control**: _Handless_ allows you to alias protocols or abstract classes to concrete implementations
- 🧠 **Fully typed**: _Handless_ uses types for bindings. It makes sure that you bind only things compatible with provided types and resolves objects with correct type
- 🧰 **Flexible**: _Handless_ allows you to provide constant values, factories or lambda functions when binding your types
- ⚡ **Async support**: _Handless_ supports async factories, async context managers, and async resolution APIs (`aresolve`)
- ↔️ **Scope shortcuts**: _Handless_ provides `Container.resolve(...)` and `Container.aresolve(...)` context-manager shortcuts for one-off resolutions
- 🎯 **Positional-only injection**: _Handless_ can autowire positional-only parameters from factories and constructors
- 🧪 **Scoped local overrides**: _Handless_ allows per-scope bindings through `Scope.bind_local(...)`

The following features are **not available yet** but planned:

- **Default values**: _Handless_ will use default values of functions or types arguments when its missing type annotation or nothing is bound for this type
- **Change default lifetime**: _Handless_ will allow you to specify the default lifetime to use any bound type to fit your needs and reduce boilerplate
- **Partial binding**: _Handless_ will provide ability to partially bind a function to a container allowing to execute that function and have the container resolve and inject its arguments on the fly
- **Pings**: _Handless_ will allow you to bind callbacks for your types allowing you to implement pings/health checks for objects interacting with shared resources (api, databases, ...
- **Captive dependencies detection**: _Handless_ will try to provide ability to detect captive dependencies due to lifetimes mismatches during binding (e.g: a singleton type depending on a transient one)

**Table of Content**

- [Explanations](#explanations)
  - [🔧 What is Dependency Injection, and Why Should You Care?](#-what-is-dependency-injection-and-why-should-you-care)
  - [🧱 What is a DI Container?](#-what-is-a-di-container)
  - [🚀 What This Library Solves](#-what-this-library-solves)
  - [🧩 Design](#-design)
    - [Container](#container)
    - [Scope](#scope)
    - [Lifetimes](#lifetimes)
- [Getting started](#getting-started)
- [Core](#core)
  - [Create a container](#create-a-container)
  - [Open a scope](#open-a-scope)
    - [Bind a value](#bind-a-value)
    - [Bind a factory function](#bind-a-factory-function)
    - [Using `factory` decorator](#using-factory-decorator)
    - [Bind a lambda function](#bind-a-lambda-function)
    - [Bind a type constructor](#bind-a-type-constructor)
    - [Bind an alias](#bind-an-alias)
  - [Manage lifetime](#manage-lifetime)
  - [Context managers and cleanup](#context-managers-and-cleanup)
    - [Factories](#factories)
    - [Values](#values)
  - [Scope local registry](#scope-local-registry)
  - [Override container bindings](#override-container-bindings)
- [Recipes](#recipes)
  - [Close container on application exits](#close-container-on-application-exits)
    - [Bind primitive types](#bind-primitive-types)
    - [Bind same type for different purposes](#bind-same-type-for-different-purposes)
    - [Bind implementations for protocols and abstract classes](#bind-implementations-for-protocols-and-abstract-classes)
    - [Static binding](#static-binding)
    - [Runtime binding](#runtime-binding)
  - [Testing](#testing)
  - [Use with FastAPI](#use-with-fastapi)
  - [Use with Typer](#use-with-typer)
  - [Add custom lifetime(s)](#add-custom-lifetimes)
- [Q&A](#qa)
  - [Why requiring having a context object to resolve types instead of using the container directly?](#why-requiring-having-a-context-object-to-resolve-types-instead-of-using-the-container-directly)
    - [Why using a fluent API to bind types as a two step process?](#why-using-a-fluent-api-to-bind-types-as-a-two-step-process)
  - [Why using objects for lifetimes? (Why not using enums or literals?)](#why-using-objects-for-lifetimes-why-not-using-enums-or-literals)
- [Alternatives](#alternatives)
- [Contributing](#contributing)

## Explanations

### 🔧 What is Dependency Injection, and Why Should You Care?

In modern software design, **dependency injection (DI)** is a technique where a component’s dependencies are **provided from the outside**, rather than hard-coded inside it. This leads to:

- ✅ More modular and testable code
- ✅ Easier substitution of dependencies (e.g., mocks, stubs, alternative implementations)
- ✅ Clearer separation of concerns

_Trivial example without DI_

```python
class Service:
    def __init__(self):
        self.db = Database()  # tightly coupled
```

_Same example with DI_

```python
class Service:
    def __init__(self, db: Database):
        self.db = db  # dependency injected
```

Doing dependency injection push creation and composition of your objects upfront. The place where you're doing this is called the [_composition root_](https://blog.ploeh.dk/2011/07/28/CompositionRoot/) and is [close to your application entrypoint(s)](https://blog.ploeh.dk/2019/06/17/composition-root-location/).

> :bulb: Your application can have many entrypoint and then many composition root, a CLI, a HTTP server, an event listener, ... Note that tests are also considered as entrypoints.

Doing dependency injection does not require any framework nor libraries, it can be achieved by "hand" (hence the name of this library "handless") by simply creating and composing your objects as expected. Doing so is called [_Pure DI_](https://blog.ploeh.dk/2014/06/10/pure-di/).

However, manually composing your objects can be challenging in complex applications, in particular when you have to manage objects with different lifetimes (one per application, one per request, and so on...). It can also be complicated to compose only parts of your object graph with some objects replaced for testing purposes or for a different entrypoint (i.e: reusing some parts of your composition logic).

> :warning: Using a dependency injection container is not mandatory. In simple applications it can be easier to do it manually. Always consider pros and cons.

This is where dependency injection containers can help you.

### 🧱 What is a DI Container?

As your project grows, wiring up dependencies manually becomes tedious and error-prone.

A dependency injection container role is to **bind** once how to create and compose each of your objects in order to get instances of them on demand. The act of asking a container to get an instance of a specific type is called **resolve**. Finally, when you don't need those instances anymore you or the container will delete them and eventually do some cleanup (if specified). This last step is known as **close**.

Dependency injection containers can also:

- 🔍 Scan constructor signatures or factory functions
- 🔗 Resolve and injecting required dependencies
- ♻️ Manage object lifetimes (singleton, transient, scoped...)
- 🧹 Handle cleanup for context-managed resources

Instead of writing all the wiring logic yourself, the container does it for you — predictably and declaratively.

### 🚀 What This Library Solves

As stated in the introduction _Handless_ provides you a dependency injection container that allows you to bind your types and how to resolve them. It also takes care of lifetimes, context managers and is fully typed. _Handless_ is able to read your types `__init__` method to determine the dependencies to inject in order to create instances.

All of this is does not require you to add any library specific decorators or attributes to your existing types.

Its API provide lot of flexibility for binding your types.

This library provides a lightweight, flexible **dependency injection container for Python** that helps you:

- ✅ **Bind** services with factories, values, aliases or constructors
- ✅ **Resolve** dependencies automatically (with type hints or custom logic)
- ✅ **Manage lifecycles** — including scope-aware caching and cleanup (singleton, transient, scoped)
- ✅ **Handle context managers** by entering and exiting created objects context managers automatically
- And more...

It’s designed to be **explicit, flexible, and intuitive**

### 🧩 Design

Here are the main concept and design choice of **Handless**.

#### Container

_Handless_ provides a `handless.Container` dependency injection container. This container allows you to **bind** Python types and define how to resolve them. You can provide a function responsible of returning an instance of the type, a constant value, an alias (i.e: another type that should be resolved instead) or using the type constructor itself. This produces a **binding**.

> :bulb: In the end, a binding is a type attached to function. This function is responsible to get an instance of the specified type based on the provided factory, value, alias or constructor.

#### Scope

In dependency injection container terminology, a scope is often referred as a kind of unique "sub container" for a short(er) duration of time. For example, in a HTTP API, you can have one scope per HTTP request. This allows to introduce a scoped lifetime to have the container create one instance of a type per scope (and then per request).

In order to resolve any types from a container, a `handless.Scope` must be used.
Most applications should open and manage scopes explicitly. For convenience,
`Container.resolve(...)` and `Container.aresolve(...)` are available as
context-manager shortcuts that open a temporary scope, resolve, yield the value,
then close it on context exit.
When called with several types, they yield a tuple of resolved values in the same
order as requested.

> :warning: You're free to manage your scopes the way you want but using a single scope for the whole application duration could be a code smell.

While you can use container-level resolve shortcuts, explicit scopes remain
the recommended way for application flows where several resolutions should share the
same scope lifecycle. This design choice has been made for two reasons:

- Avoid keeping transient values for the whole duration of a container and as a consequence, an application.
  > :question: This is because there is no reliable and easy way in Python to automatically cleanup object before garbage collection. Explicit cleanup is required or at least strongly encouraged.
- Keep scoped lifetime semantics explicit and predictable
    > :question: For types bound with a lifetime of a `Scope`, reusing a dedicated
  > scope keeps behavior obvious and avoids accidental resolve patterns where each call
  > silently creates an independent scope.

#### Lifetimes

When binding your types you can specify a lifetime. The lifetime determines when the container will execute or get a cached value of the function attached to the type to resolve:

- ##### `handless.Singleton`
  - On first resolve, the type function is called and its return value is cached for the whole duration of the container and for scopes
  - Singletons are cached in the container itself
  - Singletons context managers (if any) are entered on first resolve and exited on container end (close)
- ##### `handless.Scoped`
  - The type function is called and cached once per scope. Additional resolve on the same scope always return the same cached value
  - Scoped instances are cached per scope
  - Scoped context managers (if any) are entered on first resolve and exited on scope end (close)
- ##### `handless.Transient`
  - The type function is called on each resolve.
  - Transient values are never cached
    - Transient context managers (if any) are entered on resolve and exited on scope end (close)

> :warning: You must understand that whichever lifetime you choose the container does not actually check returned object identity. The lifetime only determines **when** the container should execute bound functions or return a previously cached value. In other words, it means that you could bind a transient type with a function returning always the same constant. You'll then end up with a singleton anyway.

> :bulb: To avoid any troubles or misunderstanding regarding lifetimes when binding factories, ensure that your **factories always create new instance of your object** and does not do any manual caching upfront. Let the container take care of caching.

## Getting started

Install it through your preferred package manager:

```shell
pip install handless
```

Once installed, you can create and use a container. Here is an example.

```python
import smtplib
from dataclasses import dataclass
from typing import Protocol

from handless import Container, Scoped, Scope, Singleton, Transient


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
container.bind(Config).to_value(config)

# User repository
container.bind(InMemoryUserRepository).to_self(Singleton())
container.bind(UserRepository).to(InMemoryUserRepository)  # type: ignore[type-abstract]

# Notification manager
container.bind(smtplib.SMTP).to_factory(
    lambda ctx: smtplib.SMTP(ctx.resolve(Config).smtp_host), Singleton(), managed=True
)
container.bind(StdoutNotificationManager).to_self(Transient())
container.bind(EmailNotificationManager).to_self()


@container.factory
def create_notification_manager(config: Config, ctx: Scope) -> NotificationManager:
    if config.smtp_host == "stdout":
        return ctx.resolve(StdoutNotificationManager)
    return ctx.resolve(EmailNotificationManager)


# Top level service
container.bind(UserService).to_self(Scoped())


with container.create_scope() as ctx:
    service = ctx.resolve(UserService)
    service.create_user("hello.world@handless.io")
    # hello.world@handless.io - Your account has been created
    print(service.get_user("hello.world@handless.io"))  # noqa: T201
    # User(email='hello.world@handless.io')  # noqa: ERA001


container.close()
```

## Core

### Create a container

To create a container simply create an instance of it. You can use your container in a context manager or manually call its `close` method to cleanup all objects resolved so far.

> :bulb: `.close()` does not prevent from reusing your container afterwards.

```python
from handless import Container

container = Container()
# Use your container and close objects on exit
with container:
    pass
# Manually close
container.close()
```

There should be at most one container per entrypoint in your application (a CLI, a HTTP server, ...). You can share the same container for all your entrypoints. A test is considered as an entrypoint as well.

> :bulb: The container should be placed on your application composition root. This can be as simple as a `bootstrap.py` file on your package root.

> :warning The container is the most "high level" component of your application. It can import anything from any sub modules. However, none of your code should depends on the container itself. Otherwise you're going to use the service locator anti-pattern. There can be exceptions to this rule, for example, when used in an HTTP API controllers (as suggested in `svcs`).

### Open a scope

To resolve any type from your container, you should usually open a scope first. The
scope should be closed when not necessary anymore.

If you only need a one-off resolution, you can use `container.resolve(...)` (or
`container.aresolve(...)`) as a shorthand context manager.

> :bulb: Opened scopes are automatically closed on container close if the scope still has a strong reference to it.

> :bulb: `scope.close()` and `await scope.aclose()` are idempotent and can be called multiple times. Closing a scope does not prevent resolving with that same scope afterwards.

```python
from handless import Container

container = Container()

# You can manually open and close your scope
ctx = container.create_scope()
ctx.resolve(...)
ctx.close()

# Or do it with a context manager
with container.create_scope():
    ctx.resolve(...)
```

Scopes are of type `handless.Scope`.

> :bulb: We did not chose `handless.Context` to avoid confusion with other contexts objects from other libraries.

### Bind a value

You can bind a value directly for your type. When resolved, the provided value will be returned as-is.

```python
from handless import Container


class Foo:
    pass


foo = Foo()
container = Container()
container.bind(Foo).to_value(foo)
with container.resolve(Foo) as resolved_foo:
    assert resolved_foo is foo
```

### Bind a factory function

If you're looking for lazy instantiating your objects you can instead bind a factory. A factory is a callable taking no or several arguments and returning an instance of the type bound. The callable can be a function, a method or even a type (a class). During resolution, the container will take care of calling the factory and return its return value. If your factory takes arguments, the container will first resolve its arguments using their type annotations and pass them to the factory.

> :warning: your callable arguments must have type annotation to be properly resolved. If missing, an error will be raised at binding time.

> :bulb: You do not need to create a dedicated factory function. There is nothing that prevents you from using an already existing function from standard library or any other library as long as it has typed parameters (or no parameters).

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
        self.bar = bar


def create_foo(bar: int) -> Foo:
    return Foo(bar)


container = Container()
container.bind(int).to_value(42)
container.bind(Foo).to_factory(create_foo)
with container.resolve(Foo) as resolved_foo:
    assert isinstance(resolved_foo, Foo)
    assert resolved_foo.bar == 42
```

#### Using `factory` decorator

Having to write your factory function somewhere then bind it on your container elsewhere tends to reduce readability. If you prefer you can opt for using the factory decorator instead.

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
        self.bar = bar


container = Container()
container.bind(int).to_value(42)


@container.factory
def create_foo(bar: int) -> Foo:
    return Foo(bar)


with container.resolve(Foo) as resolved_foo:
    assert isinstance(resolved_foo, Foo)
    assert resolved_foo.bar == 42
```

This is mostly a matter of preference as both ways do the exact same thing. You can also pass parameters to the factory decorator `@factory(lifetime=..., managed=...)`.

### Bind a lambda function

When binding a factory, you can also pass a lambda function. However, as lambdas arguments can not have type annotation it is handled differently. Lambdas can take 0 or 1 argument. If one is given, a `Scope` object will be passed, when called at resolution, as the only argument. This allows you to resolve nested types if required.

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
        self.bar = bar


container = Container()
container.bind(int).to_value(42)
container.bind(Foo).to_factory(lambda ctx: Foo(ctx.resolve(int)))
with container.resolve(Foo) as resolved_foo:
    assert isinstance(resolved_foo, Foo)
    assert resolved_foo.bar == 42
```

### Bind a type constructor

When you want to bind a type and use its constructor (`__init__` method) as its own factory, you can use the `self()` method instead of using `.factory(MyType)`.

```python
from handless import Container


class Foo:
    def __init__(self, bar: int) -> None:
        self.bar = bar


container = Container()
container.bind(int).to_value(42)
container.bind(Foo).to_self()  # Same as: container.bind(Foo).to_factory(Foo)
with container.resolve(Foo) as resolved_foo:
    assert isinstance(resolved_foo, Foo)
    assert resolved_foo.bar == 42
```

### Bind an alias

When you want a type to be resolved using resolution of another type you can define an alias.

> :bulb: Useful for binding concrete implementations to protocols or abstract classes

```python
from typing import Protocol

from handless import Container


class IFoo(Protocol):
    pass


class Foo(IFoo):
    def __init__(self) -> None:
        pass


foo = Foo()
container = Container()
container.bind(Foo).to_value(foo)
container.bind(IFoo).to(Foo)
resolved_foo = container.create_scope().resolve(IFoo)

assert resolved_foo is foo
```

When resolving `IFoo`, the container will actually resolve and returns `Foo`.

### Manage lifetime

During binding of factories `.to_factory(...)`, `@container.factory()` and `.to_self()` you can optionally pass a lifetime.

> :warning: You can not change lifetimes for `.to_value(...)` and `.to(...)` by design.

You can pass lifetimes either as positional or keyword argument. Lifetime classes can be passed directly without instantiation for concise bindings, or as instances for explicitness.

```python
from handless import Container, Singleton, Transient, Scoped


container = Container()
# Singleton - pass class or instance
container.bind(object).to_factory(lambda: object(), Singleton)  # class (concise)
container.bind(object).to_factory(lambda: object(), Singleton())  # instance (explicit)
# Scoped
container.bind(object).to_factory(lambda: object(), Scoped)
container.bind(object).to_factory(lambda: object(), Scoped())
# Transient (The default)
container.bind(object).to_factory(lambda: object(), Transient)
container.bind(object).to_factory(lambda: object(), Transient())
```

[As described above](#lifetimes), lifetimes allow to determine when the container will execute types factory and cache their result. Generally speaking you may use:

- `handless.Singleton` for any objects that should be a singleton for your whole application (one and only one instance per application). For example a HTTP connection pool
  > :warning: Singleton should be threadsafe in multi threaded application to avoid any issues
- `handless.Scoped` for objects that should be unique per context. For example, a database session should be unique per HTTP request
- `handless.Transient` (the default) for stateful objects which should not be shared because their use rely on their internal state. For example an opened file

### Context managers and cleanup

Containers and contexts can take care of entering and exiting objects with context managers. Both has a `close` function which clear their cache and exits any entered context managers.

#### Factories

Object returned by functions bound with `.to_factory(...)` or `.to_self()` are automatically entered on resolve and exited on close if it is context managers.

> :bulb: You can disable this default behavior by passing `managed=False`. However, passing `False` is disallowed if the object return is NOT an instance of the given type.

> :warning: Objects are only entered when resolved. Cached values are NOT re-entered afterwards.

If you pass a function which is a generator it will be automatically wrapped as a context manager (`contextlib.contextmanager`).

> :bulb: You pass a function already decorated with `contextlib.contextmanager` and it will work as expected.

#### Values

Objects bound with `.to_value(...)` are NOT entered by default. If you want their context manager to be handled for you you must pass `.to_value(..., managed=True)`.

> :question: Passing a value means that this value has been created outside of the container and then its lifetime should not container's responsibility.

### Scope local registry

If you need to override or add bindings for a single scope only, use
`scope.bind_local(...)`. These local bindings have higher priority
than container bindings, and only affect the current scope.

```python
from handless import Container

container = Container()
container.bind(str).to_value("global")

with container.create_scope() as scope:
    scope.bind_local(str).to_value("scope-local")
    assert scope.resolve(str) == "scope-local"

with container.create_scope() as scope:
    assert scope.resolve(str) == "global"
```

### Override container bindings

Containers does not allow to bind the same type twice. The following code will raise an error.

```python
from handless import Container

container = Container()
container.bind(str).to_value("Hello")
container.bind(str).to_value("This will raise an error!")
```

In order to override your container bound types you must use the `override(...)` function instead. This function works identically to `bind(...)`.

```python
from handless import Container

container = Container()
container.bind(str).to_value("Hello")


def test_my_container():
    container.override(str).to_value("Overridden!")
    with container.create_scope() as ctx:
        resolved = ctx.resolve(str)
        assert resolved == "Overridden!"
```

> :warning: Overriding is primarily made for testing purposes. You should not use overriding in your production code. If you have use cases where it could makes sense please open a ticket.

Please also note the following:

- Overrides can be overridden as well (each override erases the previous one)
- Overrides always take precedence over bound type whatever his lifetime (even if the type was previously resolved and cached)
- Overrides are automatically erased when the container is closed
- On container close, all overrides (even erased one) as well as any previously bound types are properly closed as well

## Recipes

### Close container on application exits

If your application has no shutdown mechanism you can register your container `close` method using `atexit` module to close on program exit.

```python
import atexit

from handless import Container

container = Container()

atexit.register(container.close)
```

Closing the container is idempotent and can be used several times. Each call clears singletons and exits entered context managers, if any. Closing also does not prevent using the container afterwards.

### Bind primitive types

:construction: Under construction

### Bind same type for different purposes

:construction: Under construction

### Bind implementations for protocols and abstract classes

Dependency injection is a key enabler for inversion of control where your objects depends on abstractions or interfaces rather than actual implementation. This mechanism prevents tight coupling between your objects and allows you to swap dependencies with different implementations. This mechanism is mostly used for testing purposes to replace real implementations with fakes or mocks.

`handless` allows you to do so through various mechanisms. Let's consider you defined an interface of a repository with two implementations, one fo mongoDB and another for SQLite.

> :warning: Unrelevant details have been removed for readability.

```python
from typing import Protocol

from handless import Container


class TodoItemRepository(Protocol):
    def add(self, todo: dict) -> None: ...


class MongoTodoItemRepository(TodoItemRepository):
    def __init__(self, mongo_url: str) -> None: ...

    def add(self, todo: dict) -> None: ...


class SqliteTodoItemRepository(TodoItemRepository):
    def __init__(self) -> None: ...

    def add(self, todo: dict) -> None: ...


container = Container()
```

#### Static binding

The most simple case is when you want to statically define which implementation use. Then you'll eventually override this during your tests.

```python
# Individually bind your implementations
container.bind(SqliteTodoItemRepository).to_self()
container.bind(MongoTodoItemRepository).to_factory(
    lambda ctx: MongoTodoItemRepository(os.getenv("DB_URL"))
)

# Bind an alias of your protocol against your choice
container.bind(TodoItemRepository).to(SqliteTodoItemRepository)  # type: ignore[type-abstract]

with container.create_scope() as ctx:
    repo = ctx.resolve(TodoItemRepository)  # type: ignore[type-abstract]
    assert isinstance(repo, SqliteTodoItemRepository)
```

> :warning: Mypy does not like calling the `.bind` and `.resolve` functions on `typing.Protocol` nor `abc.ABC` hence the type ignore magic comment.

#### Runtime binding

There can also be situations where you want to pick implementation at runtime depending on some conditions. For this, you can use a factory that will resolve the correct implementation.

```python
import os

from handless import Singleton, Scoped, Scope


container.bind(SqliteTodoItemRepository).to_self()
container.bind(MongoTodoItemRepository).to_factory(
    lambda ctx: MongoTodoItemRepository(os.getenv("DB_URL"))
)


@container.factory
def get_todo_item_repository(ctx: Scope) -> TodoItemRepository:
    db_type = os.getenv("DB_TYPE", "sqlite")
    if db_type == "sqlite":
        return ctx.resolve(SqliteTodoItemRepository)
    if db_type == "mongo":
        return ctx.resolve(MongoTodoItemRepository)
    raise ValueError(f"Unknown database type: {db_type}")
```

> :bulb: Use of the factory decorator is not mandatory. You can achieve the same with the binding API (`container.bind(...)`).

> :warning: Most of the time you should use a `Transient` lifetime (the default) for the factory resolving your abstract or protocol to avoid lifetimes mismatches. Indeed, if you use a `Singleton` lifetime on `get_todo_item_repository` while one of your implementation is `Transient` or `Scoped` you'll end up with a [captive dependency](https://blog.ploeh.dk/2014/06/02/captive-dependency/).

### Testing

> :construction: Under construction

### Use with FastAPI

> :construction: Under construction

### Use with Typer

> :construction: Under construction

### Add custom lifetime(s)

> :construction: Under construction

## Q&A

### Why requiring having a context object to resolve types instead of using the container directly?

- Separation of concerns
- Simpler API
- Transient dependencies captivity
- Everything is a context
- Easier management and cleanup of resolved values

### Why using a fluent API to bind types as a two step process?

- type hints limitations

### Why using objects for lifetimes? (Why not using enums or literals?)

- Allow creating its own lifetimes
- Allows to add options in the future
- Avoid if statements

## Alternatives

Other existing alternatives you might be interested in:

- [lagom]
- [svcs]
- [dependency_injector]

## Contributing

Running tests: `uv run nox`

> :warning: As this library support both sync and async functions, tests have been duplicated for simplicity. Whenever you add, remove or change an existing test in `test_resolve.py` or `test_resolve_async.py` don't forget to update each others.

[dependency_injector]: https://python-dependency-injector.ets-labs.org/
[lagom]: https://lagom-di.readthedocs.io
[svcs]: https://svcs.hynek.me/
