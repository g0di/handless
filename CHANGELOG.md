# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `Container.resolve(...)` and `Container.aresolve(...)` context-manager shortcuts to resolve one or several types using a temporary scope and keep them alive until context exit.

### Changed

- **Breaking:** registration terminology has been renamed to binding terminology across the public API:
  - `Container.register(...)` has been renamed to `Container.bind(...)`
  - `Scope.register_local(...)` has been renamed to `Scope.bind_local(...)`
  - `Registration` has been renamed to `Binding`
  - `RegistrationBuilder` has been renamed to `Binder`
  - Exception names have been renamed: `RegistrationError` -> `BindingError`, `RegistrationNotFoundError` -> `BindingNotFoundError`, `RegistrationAlreadyExistError` -> `BindingAlreadyExistsError`.
  - Legacy exception aliases (`RegistrationError`, `RegistrationNotFoundError`, `RegistrationAlreadyExistError`) have been removed.
  - Fluent binder methods were renamed: `.factory(...)` -> `.to_factory(...)`, `.value(...)` -> `.to_value(...)`, `.alias(...)` -> `.to(...)`, `.self(...)` -> `.to_self(...)`
  - Decorator renamed: `@container.factory()` -> `@container.binding()` (noun form for declarative binding marker)
- `Binder.to_self(...)` and `Binder.to_factory(...)` now accept `lifetime` as positional argument in addition to keyword argument.
- Lifetime parameters in `.to_self(...)`, `.to_factory(...)`, and `@container.binding()` now accept lifetime classes (e.g., `Singleton`, `Scoped`, `Transient`) in addition to lifetime instances (e.g., `Singleton()`, `Scoped()`, `Transient()`). This allows for more concise bindings without explicit instantiation.
- **Breaking:** renamed binding option `enter` to `managed` across `Binder.to_self(...)`, `Binder.to_value(...)`, `Binder.to_factory(...)`, `Container.binding(...)` and `Binding` (`enter` field is now `managed`).
- **Breaking:** renamed cleanup methods from `release()`/`arelease()` to `close()`/`aclose()` on container and scope objects.
- **Breaking:** replaced resolution context terminology with scope terminology across the public API:
  - `ResolutionContext` has been renamed to `Scope`
  - `Contextual` lifetime has been renamed to `Scoped`
  - `Container.open_context()` has been renamed to `Container.create_scope()`
- Resolution failures now raise a single `ResolutionError` carrying the full dependency chain and the original root-cause exception for both `resolve()` and `aresolve()`.
- `ResolutionError` now exposes explicit `outer_type` and `inner_type` properties derived from `resolution_chain`, and adds `root_cause` access to the underlying exception. Its string formatting is now split between a concise `str()` message and a diagnostic `repr()` including the full chain.
- Improved public API docstrings across container, scope, binding, lifetime and exceptions modules.
- Added and refined doctest examples for key public APIs, including lifetime strategies and scope/container resolution shortcuts.
- Updated README capability matrix and core docs to match shipped behavior (async support, positional-only autowiring, and scope-local bindings), and corrected related wording/typos.

## [0.3.0] - 2025-09-25

### Added

- Added async support allowing to register and resolve `aresolve()` async factories and context managers. Async functions have been added to existing objects and prefixed with a `a`. This choice has been made to simplify smooth migration of a sync codebase using `handless` to async without having to rewrite everything. It is also easier to use with some frameworks like `fastapi` where one can mix both sync and async functions.

### Changed

- Module `handless.container` is now private. Its main content is now importable from `handless` directly

### Removed

- The `handless.lifetimes.get_context_for` function to attach lifetime contexts to objects has been moved in `handless.lifetimes.LifetimeContext` as `get()` class method

## [0.2.1] - 2025-08-17

### Fixed

- Resolution of bindings with singleton lifetime is now threadsafe. Two context trying to resolve a same singleton at the same time will end up with the exact same value

## [0.2.0] - 2025-08-11

### Added

- Added documentation to README.md file including but not limited to:
  - Binding API
  - Context managers & cleanup
  - Types resolving
  - Bindings overrides
  - Release container on application exits recipe
  - Register implementations for protocols and abstract classes recipe
  - Alternatives section
- Added `container.override(...)` method to override registered types with different value or factory for testing purposes

### Removed

- `typing-extensions` is not required anymore

### Internals

- Add `mdformat` and `mdformat-ruff` to properly format markdown files and Python code blocks using `ruff`

## [0.1.0] - 2025-07-16

This version does a major change to the public API. Now `Container` is the main object to be used to register types in the container. To resolve, one must uses a `ResolutionContext` obtained by running `open_context()` function on the container. This produces a context allowing to resolves types and track entered context managers and cache objects.

### Added

- `factory` registry decorator now properly register generators decorated with the `contextmanager` decorator.
- Added ability to override container dependencies at scope level using `bind_local()` function.
- Added a function `self()` to register a type and use it as its own factory

### Removed

- The `Registry` object

### Changed

- One must now use objects for lifetimes instead of literals, `Singleton`, `Contextual`, `Transient`.
- Renamed to `lookup` the function to get a binding for a type
- Changed the binding API which now use method chaining for registering either value, factory or alias.
- Replaced `Scope` with `ResolutionContext`
- `close()` method for `Container` and `ResolutionContext` has been renamed to `release()`

### Internals

- Bindings has now has a reference to the type to which it is binded
- Extracted the context containaing cached resolved types and entered context managers into a dedicated object which is not tied to `Container` nor `ResolutionContext` directly.

## [0.1.0-alpha.2] - 2025-04-07

### Added

- Added short documentation on how to use the library ([README.md](./README.md))

### Changed

- `ServiceDescriptor` has been renamed to `Provider`
- Shorthands to create providers has been put as class methods directly into the `Provider` class
- `Registry` public API has been fully replaced by `register` function and `provider` decorator to fit most use cases
- Set as private all internals and core of the library

### Removed

- Removed the `BaseContainer` abstract class which has been merge with the `Container` itself.

### Internals

- Add `PyInvoke` and tasks for managing the project

## [0.1.0-alpha.1]

### Added

- `Registry` - for registering services by type including values, factories, scoped factories, singletons, aliases
- Imperative services binding - through `register`, `register_*` and dict like `reg.lookup(Service) = ...` functions
- Declarative services binding - through decorators `@factory`, `@singleton`, `@scoped`
- Manual wiring - lambda can be used as factories with optionally a single argument to receive the container
- Autowiring - The container uses factories and classes constructors arguments type hints to resolve and inject nested dependencies
- `Container` - for resolving services from registry
- `ScopedContainer` - using registry and parent container to resolve services for a scoped lifetime (http request for example)

[0.1.0]: https://github.com/g0di/handless/releases/tag/0.1.0
[0.1.0-alpha.1]: https://github.com/g0di/handless/releases/tag/0.1.0-alpha.1
[0.1.0-alpha.2]: https://github.com/g0di/handless/releases/tag/0.1.0-alpha.2
[0.2.0]: https://github.com/g0di/handless/releases/tag/0.2.0
[0.2.1]: https://github.com/g0di/handless/releases/tag/0.2.1
