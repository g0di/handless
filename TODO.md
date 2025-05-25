# TODOs

This document contains all the ideas I've got for new features or changes to be made.

## TOP PRIORITY

- maybe rollback to registry.register(...).factory() API and container.resolve() rather than get.
- find better way to manage scopes/lifetimes
- add tests for covering uncovered code

> :bulb: The order does not reflect the priority.

## Documentation

- :books: Mention the mypy `type-abstract` issue when registering abstract **classes** or protocols and how to disable it
- :books: Mention the the fact that callable objects can not be registered as factory implicitly
- :books: Find out how to verify code examples in the **documentation**
- :books: Find out how to format code examples in the doc (readme)
- :books: Build a static documentation website using `sphinx` or `mkdocs` published on github pages
- :books: Add badges on README file (coverage, tests, ...)
- :books: add/enhance docstrings

## Context managers

- :new: add a function for manually releasing a value from the container (only affect transient) to prevent transient context managers to stay until container is closed (this one might be superseded by the change to make container a scoped container by default)
- :new: prevent ability to pass enter=False when providing a factory returning a context manager which **enter** method does not return an instance of expected object
  - This must be managed through typings because we can not ensure at runtime that a function returns a particular value without calling it
- :new: Allow to pass an object which is not an instance of registered type but which is a context manager of given type (with enter=True being mandatory)

## Async

- :new: add handling of async factories
- :new: add handling of async context managers

## Resolving

- :new: Handle factories/types positional only arguments
- :new: Handle factories/types arguments with default values. If the container can not resolve one, leave the default value instead.
  - :new: Do not raise error if registering a function missing type annotations for argument having default value.
- :new: add a decorator to container for resolving and injecting function parameters when executed.

## Misc

- :bug: On resolve error print the full resolving stack for debugging
- :bug: When logging service type resolved, also display the full requiremnt chain (maybe under debug level)
- :bug: Make resolving singletons threadsafe (add a lock)
- :new: add function for resolving all services in the container for testing purposes
- :new: add function for verifying lifetimes mistmatches on registry (e.g: singleton depending on transint)
- :bug: Add a function for printing the whole dependency tree with lifetimes
- :new: Add ping functions and ability to health check services in the container
- Use only tox (or nox) to manage all our QA commands
- Use pyInvoke for having command for quickly creating a github release

## Registration

- :new: allow to pass providers directly to the register function (the register function should adapt default values for enter/lifetime accordingly)
- :new: Use classes for services lifetimes (internally only)
  - This will allow to add parameters to lifetimes to enhance their behavior
  - This will allow to rely on polymorphism rather than if/else for adapting container resolve method
- :new: Add a function for updating one registry with another
- :new: add ability to copy a registry
- :new: Add ability to register local values on (scoped) container to inject, for example, HTTP request scoped objects or anything from other frameworks
- :bug: Registering a type with itself must ensure the given type is not abstract or protocol
- :bulb: Suggest on additional kind of registry providing a different public API for registering (could be based on Castle Windsor or InversifyJS)
- :new: add new lifetimes (threaded, pooled)

## Testing

- :wrench: Maybe merge resolving/registering tests to avoid having to rely on `Provider` internal class.
- :wrench: Add ability to temporarily override container/registry for testing purposes
- :wrench: Use nox for local testing on many python versions

## github

- Publish code coverage (codecov?)
- enable build on PRs
