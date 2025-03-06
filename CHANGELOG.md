# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha.1]

### Added

- `Registry` - for registering services by type including values, factories, scoped factories, singletons, aliases
- Imperative services registration - through `register`, `register_*` and dict like `reg[Service] = ...` functions
- Declarative services registration - through decorators `@factory`, `@singleton`, `@scoped`
- Manual wiring - lambda can be used as factories with optionally a single argument to receive the container
- Autowiring - The container uses factories and classes constructors arguments type hints to resolve and inject nested dependencies
- `Container` - for resolving services from registry
- `ScopedContainer` - using registry and parent container to resolve services for a scoped lifetime (http request for example)
