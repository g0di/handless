# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2025-08-17

### Fixed

- Resolution of registrations with singleton lifetime is now threadsafe. Two context trying to resolve a same singleton at the same time will end up with the exact same value

## [0.2.0] - 2025-08-11

### Added

- Added documentation to README.md file including but not limited to:
  - Registration API
  - Context managers & cleanup
  - Types resolving
  - Registrations overrides
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
- Added ability to override container dependencies at scope level using `register_local()` function.
- Added a function `self()` to register a type and use it as its own factory

### Removed

- The `Registry` object

### Changed

- One must now use objects for lifetimes instead of literals, `Singleton`, `Contextual`, `Transient`.
- Renamed to `lookup` the function to get a binding for a type
- Changed the registration API which now use method chaining for registering either value, factory or alias.
- Replaced `Scope` with `ResolutionContext`
- `close()` method for `Container` and `ResolutionContext` has been renamed to `release()`

### Internals

- Registrations has now has a reference to the type to which it is binded
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
- Imperative services registration - through `register`, `register_*` and dict like `reg.lookup(Service) = ...` functions
- Declarative services registration - through decorators `@factory`, `@singleton`, `@scoped`
- Manual wiring - lambda can be used as factories with optionally a single argument to receive the container
- Autowiring - The container uses factories and classes constructors arguments type hints to resolve and inject nested dependencies
- `Container` - for resolving services from registry
- `ScopedContainer` - using registry and parent container to resolve services for a scoped lifetime (http request for example)

[0.1.0]: https://github.com/g0di/handless/releases/tag/0.1.0
[0.1.0-alpha.1]: https://github.com/g0di/handless/releases/tag/0.1.0-alpha.1
[0.1.0-alpha.2]: https://github.com/g0di/handless/releases/tag/0.1.0-alpha.2
[0.2.0]: https://github.com/g0di/handless/releases/tag/0.2.0
[0.2.1]: https://github.com/g0di/handless/releases/tag/0.2.1
