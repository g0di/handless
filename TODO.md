# TODOs

This document contains all the ideas I've got for new features or changes to be made.

> :bulb: The order does not reflect the priority.

## Agent

- Align cleanup failure semantics with ExitStack behavior:

  - Do not silently swallow teardown exceptions in close and aclose.
  - Aggregate/propagate teardown failures after attempting all exits.
  - Add tests for exception propagation in sync and async cleanup paths.

- Define precedence contract for overrides vs scope-local bindings:

  - Container overrides must take precedence over everything, including scope-local bindings.
  - Update lookup order and behavior docs to reflect this rule.
  - Add tests for all combinations: registered vs override vs scope-local, including cached instances.

- Make sync/async resolution behavior deterministic without splitting caches:

  - Keep a single cache to preserve singleton/scoped identity.
  - Classify bindings by execution mode (sync-only vs async-capable).
  - Enforce mode before cache access so resolve and aresolve behavior does not depend on cold/warm cache state.
  - Add tests covering both cold and cached paths for sync and async APIs.

- Activate dependency default fallback behavior:

  - During resolution, if a dependency cannot be resolved and the parameter has a default value, use that default instead of failing.
  - Keep strict failure for missing dependencies without defaults.
  - Add sync and async tests for mixed required/defaulted dependency signatures.
  - Document clearly that defaults are runtime fallback only when dependency lookup fails.

- Add runtime container validation API:

  - Introduce a container.validate() method to analyze the full binding graph after bootstrap.
  - Detect and report captive dependencies (lifetime mismatches), unresolved required dependencies, and sync/async incompatibilities.
  - Support both non-raising report mode and strict fail-fast mode.
  - Keep validation side-effect free and runnable in tests/CI/startup.

## Documentation

- :books: Find out how to verify code examples in the **documentation** and automate it
- :books: Build a static documentation website using `sphinx` or `mkdocs` published on github pages
- :books: Add badges on README file (coverage, tests, ...)
- :books: Document `on_release` callback

## Async

- :hourglass: add handling of async iterators and wrap them as async context managers
- :hourglass: Test that a warning is raised when closing container/scope while some async context managers are still open
- :hourglass: Test that resolving an async factory with sync resolve raise a type error

## Resolving

- :new: Handle factories/types arguments with default values. If the container can not resolve one, leave the default value instead.
  - :new: Do not raise error if registering a function missing type annotations for argument having default value.
- :new: add a decorator to container for resolving and injecting function parameters when executed.

## Misc

- Maybe raise errors collected while exiting all entered context managers rather than just logging them and continuing silently (take ExitStack as example)
- :bug: When logging service type resolved, also display the full requiremnt chain (maybe under debug level)
- :new: add function for resolving all services in the container for testing purposes
- :new: add function for verifying lifetimes mistmatches on registry (e.g: singleton depending on transint)
- :bug: Add a function for printing the whole dependency tree with lifetimes
- :new: Add ping functions and ability to health check services in the container

## Binding

- :new: Add functions for copying a container
- :new: Add ability to register local values on scopes, for example, HTTP request scoped objects or anything from other frameworks
  - We must find a way to allow container overrides to still override those local values
- :bug: Registering a type with itself must ensure the given type is not abstract or protocol
- :new: add new lifetimes (threaded, pooled)
- :new: add ability to choose default lifetime at container level
- :new: add auto_registration capabilities so container is able to resolve types not registered
- :new: use magic attributes (**handless_lifetime**) for auto resolving lifetimes from types
- :new: Allow to configure containers through yaml/toml files
- :new: Add ability to register release callback per binding (for values for exemples)

## Tests

- add tests for covering uncovered code
- Split unit tests into smaller files (one per binding type, one per resolve lifetime, ...)

## github

- Publish code coverage (codecov?)
- enable build on PRs
