## doc

- Mention the mypu type-abstract issue and how to disable it
- Mention the caveat for singletons and callables objects

## Context management

- add handling of context managers
  - add a function for manually releasing a value from the container -> Not sure if useful
  - If possible, find a way to clear transient factories before having to call close
- prevent ability to pass enter=False when providing a factory returning a context manager which **enter** method does not return an instance of expected object
  - This must be managed through typings because we can not ensure at runtime that a function returns a particular value without calling it

## Async

- add handling of async factories
- add handling of async context managers

## Resolving

- use "get" as name for resolving from container
- Handle positional only argument
- When resolving type/factory parameters, inject default values if not able to resolve

## Misc

- add resolve stack for debugging
- When logging service type resolved, also display the full requiremnt chain
- handle resolving singleton from different threads (add a lock)
- add function for resolving all services in container for testing purposes
- add function for verifying scopes validities on registry
- add docstrings
- Update readme file
- create a real documentation page
- Add a function for printing the whole dependency tree with lifetimes

## Registration

- do not raise error if registering a function missing type annotations for argument having default value.
- Maybe add a public register_factory function for registering classes and typed functions directly
- remove most doc from provider since this is not part of public API
- Use actual classes for services lifetimes
  - This will allow to add parameters to lifetimes to enhance their behavior
  - This will allow to rely on polymorphism rather than if/else for adapting container resolve method
  - Add a function for updating one registry with another
- add ability to copy a registry
- add ability to register local values on scoped container to inject, for example, HTTP request scoped objects
- registering a type with itself must ensure the given type is not abstract or protocol

## Testing

- Update unit tests for our handling of lambda functions
- Maybe merge resolving/registering tests
- add ability to copy registry/containers for testing purposes
- add ability to temporarily override container/registry for testing purposes
- use nox for local testing on many python

# github

- Add readme badges (tests, coverage, ...)
- Publish code coverage (codecov?)
- enable build on PRs + other nice stuff
