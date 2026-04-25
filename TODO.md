# TODOs

This document contains all the ideas I've got for new features or changes to be made.

> :bulb: The order does not reflect the priority.
>
## Agent

- Fix README capability drift:
  - Remove or update outdated "not available yet" items that are already shipped.
  - In particular, README currently says async support and positional-only autowiring are missing, but code/tests/changelog show they are implemented.
  - Keep README, changelog, and tested behavior aligned before next release.
- Align cleanup failure semantics with ExitStack behavior:
  - Do not silently swallow teardown exceptions in release and arelease.
  - Aggregate/propagate teardown failures after attempting all exits.
  - Add tests for exception propagation in sync and async cleanup paths.
- Add this to the Agent section in TODO.md for the lambda recommendation:
  - Narrow implicit context injection rule:
  - Keep one-arg untyped fallback only for lambda factories.
  - For non-lambda callables, require explicit ResolutionContext annotation and fail fast otherwise.
  - Document this as an intentional ergonomic exception for concise registrations.
- Use the the name `managed` as keyword argument instead of `enter` during registration
- Use the term "Scope" instead of context for our container to avoid misunderstanding
  - Use `create_scope` instead of `open_context`
  - Use `Scoped` instead of `Contextual` lifetime
  - Use `scope` instead of `ctx`
  - Use `Scope` instead of `ResolutionContext`
- Improve resolution error diagnostics:
  - When resolution fails, include the full resolution chain (requested type plus dependency path).
  - Preserve and expose the root cause exception that actually broke resolution.
  - Apply this consistently to sync resolve and async resolve.
  - Add tests covering nested failure chains and verify message/metadata content.
- Define precedence contract for overrides vs scope-local registrations:
  - Container overrides must take precedence over everything, including scope-local registrations.
  - Update lookup order and behavior docs to reflect this rule.
  - Add tests for all combinations: registered vs override vs scope-local, including cached instances.
- Make sync/async resolution behavior deterministic without splitting caches:
  - Keep a single cache to preserve singleton/contextual identity.
  - Classify registrations by execution mode (sync-only vs async-capable).
  - Enforce mode before cache access so resolve and aresolve behavior does not depend on cold/warm cache state.
  - Add tests covering both cold and cached paths for sync and async APIs.
- Activate dependency default fallback behavior:
  - During resolution, if a dependency cannot be resolved and the parameter has a default value, use that default instead of failing.
  - Keep strict failure for missing dependencies without defaults.
  - Add sync and async tests for mixed required/defaulted dependency signatures.
  - Document clearly that defaults are runtime fallback only when dependency lookup fails.
- Add runtime container validation API:
  - Introduce a container.validate() method to analyze the full registration graph after bootstrap.
  - Detect and report captive dependencies (lifetime mismatches), unresolved required dependencies, and sync/async incompatibilities.
  - Support both non-raising report mode and strict fail-fast mode.
  - Keep validation side-effect free and runnable in tests/CI/startup.

## Documentation

- :books: Find out how to verify code examples in the **documentation** and automate it
- :books: Build a static documentation website using `sphinx` or `mkdocs` published on github pages
- :books: Add badges on README file (coverage, tests, ...)
- :books: add/enhance docstrings
- :books: Add documentation on ability to register local types on resolution context
- :books: Document `on_release` callback

## Async

- :hourglass: add handling of async iterators and wrap them as async context managers
- :hourglass: Test that a warning is raised when closing container/context while some async context managers are still open
- :hourglass: Test that resolving an async factory with sync resolve raise a type error

## Resolving

- :new: Add a context manager only function at container level to resolve types as a shortcut with opening a context, resolving type then exits
- :new: Handle factories/types arguments with default values. If the container can not resolve one, leave the default value instead.
  - :new: Do not raise error if registering a function missing type annotations for argument having default value.
- :new: add a decorator to container for resolving and injecting function parameters when executed.

## Misc

- Maybe raise errors collected while exiting all entered context managers rather than just logging them and continuing silently (take ExitStack as example)
- I'm hesitating into renaming `release` function to `close` and `resolve` to `get` to make it more pythonic and shorter. I'm also not so much fan of the name ResolutionContext and LifetimeContext, all those context are misleading. Maybe I should revert resolution context into scope and LifetimeContext to some LifetimeState or LifetimeCache?
- :new: On resolve error, do not chain resolve exception, keep the latest one, with the whole resolve chain and the root cause of the error
- :bug: When logging service type resolved, also display the full requiremnt chain (maybe under debug level)
- :new: add function for resolving all services in the container for testing purposes
- :new: add function for verifying lifetimes mistmatches on registry (e.g: singleton depending on transint)
- :bug: Add a function for printing the whole dependency tree with lifetimes
- :new: Add ping functions and ability to health check services in the container

## Registration

- :new: Add functions for copying a container
- :new: Add ability to register local values on contexts, for example, HTTP request scoped objects or anything from other frameworks
  - We must find a way to allow container overrides to still override those local values
- :bug: Registering a type with itself must ensure the given type is not abstract or protocol
- :new: add new lifetimes (threaded, pooled)
- :new: add ability to choose default lifetime at container level
- :new: add ability to pass lifetime class instead of instances
- :new: add auto_registration capabilities so container is able to resolve types not registered
- :new: use magic attributes (**handless_lifetime**) for auto resolving lifetimes from types
- :new: Allow to configure containers through yaml/toml files
- :new: Add ability to register release callback per registration (for values for exemples)

## Tests

- add tests for covering uncovered code
- Split unit tests into smaller files (one per registration type, one per resolve lifetime, ...)

## github

- Publish code coverage (codecov?)
- enable build on PRs
