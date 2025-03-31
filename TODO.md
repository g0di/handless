Notes for myself:

- Whatever API we use for registering passing an abstract or protocol type to be registered always lead mypy to complete about abstract class
- However, it will properly ensure the second given value match that abstract class

ATM we can:

- Provide register\_\* functions for explicitly registering stuff (singleton, scoped, factory, implementation, ..., pooled, threaded)
- Provide decorators for singleton, factory, scoped, pooled and threaded
- Provide the register() function which will register a service descriptor only (no implicit registration)
- Provide another public API for binding through chain calls as experimentation
- Update the service descriptor class to use chained functions for building it

We will end up with three ways to register srvices:

- Explicitly using functions
- Explicitly using a service descriptor class directly
- Using a binder

## Context management

- add handling of context managers
  - add a function for manually releasing a value from the container -> Not sure if useful
  - If possible, find a way to clear transient factories before having to call close
- prevent ability to pass enter=False when providing a factory returning a context manager which **enter** method does not return an instance of expected object
  - This must be managed through typings because we can not ensure at runtime that a function returns a particular value without calling it
  - Maybe just add a dev warning when a type is resolved with an object not being an instance of it.

## Async

- add handling of async factories
- add handling of async context managers

## Resolving

- Handle positional only argument
- Simply inject getters parameters default value if we could not resolve its type
- Consider mark regitry as strict rather than container itself

## Misc

- Fix the type-abstract mypy issues
- add resolve stack for debugging
- When logging service type resolved, also display the full requiremnt chain
- handle resolving singleton from different threads (add a lock)
- add function for resolving all services in container for testing purposes
- add function for verifying scopes validities on registry
- add docstrings
- Update readme file
- create a real documentation page
- Move private API on private modules and prefix private stuff with leading underscore
- Add a function for printing the whole dependency tree with lifetimes

## Registration

- Use actual classes for services lifetimes
  - This will allow to add parameters to lifetimes to enhance their behavior
  - This will allow to rely on polymorphism rather than if/else for adapting container resolve method
- add function for registering many services in one call in the registry
  - We may also add a function for updating one registry with another
- add ability to copy a registry
- add ability to register local values on scoped container to inject, for example, HTTP request scoped objects
- registering a type with itself must ensure the given type is not abstract or protocol

## Testing

- add ability to copy registry/containers for testing purposes
- add ability to temporarily override container/registry for testing purposes

# github

- Add readme badges (tests, coverage, ...)
- Publish code coverage (codecov?)
- enable build on PRs + other nice stuff
