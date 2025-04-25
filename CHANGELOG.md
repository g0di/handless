# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `factory` registry decorator now properly register generators decorated with the `contextmanager` decorator.
- Added ability to override registry dependencies during tests

### Changed

- Renamed to `lookup` the function to get a binding for a type.
- Rename to `factory` the registry function for decorating function and register them as factories. It better aligns with the new registration API.
- Rename container `resolve` method to `get`
- Registry does not allow to override previously registered types by default. An `allow_direct_overrides` option has been added to bypass this default behavior. This has been made in order to prevent accidentaly overriding a previous binding.
- Changed the registration API which now use method chaining for registering either value, factory, alias, lambda or provider. This API provide better type checking and cover all use cases at the cost of the fluent API (you can no longer chain call the register method). It is also more explicit on what it does rather than relying on the previous magic registration method. Finally it simplify extending it in the future if required.
- providers modules is now public. You can directly use them along the `provider` registration method as well as create your own custom providers through subclassing.

### Internals

- Bindings `factory` attribute have been renamed to `provider` which corresponds to a brand new `Provider` class tailored at producing objects for container. This better separate concerns, clarify the code and facilitates ability to add new providers in the future.
- Bindings has now has a reference to the type to which it is binded
- Created dedicated classes for each lifetimes. This simplify container having the right behavior depending on the lifetime and remove need for the if/else statements. This clarify the code and will simplify adding new lifetimes in the future as well as being able to add parameters to them.
- Renamed `ScopedContainer` to `Scope`

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

[unreleased]: https://github.com/g0di/handless/compare/0.1.0-alpha.2...HEAD
[0.1.0-alpha.2]: https://github.com/g0di/handless/compare/0.1.0-alpha.1...0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/olivierlacan/keep-a-changelog/releases/tag/0.1.0-alpha.1
