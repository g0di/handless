## Context management

- add handling of context managers
  - add a function for manually releasing a value from the container -> Not sure if useful
  - If possible, find a way to clear transient factories before having to call close
- prevent ability to pass enter=False when providing a factory returning a context manager which **enter** method does not return an instance of expected object

## Async

- add handling of async factories
- add handling of async context managers

## Resolving

- Handle positional only argument

## Misc

- Fix the type-abstract mypy issues
- add resolve stack for debugging
- When logging service type resolved, also display the full requiremnt chain
- handle resolving singleton from different threads
- add function for resolving all services in container for testing purposes
- add function for verifying scopes validities at registration time
- add log messages/dev warnings when there is scopes mismatches
- add docstrings
- Update readme file
- create a real documentation page
- Move private API on private modules and prefix private stuff with leading underscore
- Add a function for printing the whole dependency tree with lifetimes

## Registration

- add function for registering many services in one call in the registry
  - We may also add a function for updating one registry with another
- add ability to register local values on scoped container to inject, for example, HTTP request scoped objects
- registering a type with itself must ensure the given type is not abstract or protocol
- Allow to `registry[MyType] = Factory()` to autouse the type itself
- Think about ability to create a container using a Pydantic like Model where fields are types to register

```python

class MyContainer(ContainerModel):
  my_service: MyService = Factory()
  my_service: MyService = Singleton(MyServiceImpl)
  my_service: MyService = Singleton(lambda c: ...)
  my_service: Annotated[MyService, Singleton(...)]

MyContainer().my_service # resolve
```

## Testing

- add ability to copy registry/containers for testing purposes
- add ability to temporarily override container/registry for testing purposes
