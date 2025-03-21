## Context management

- add handling of context managers
  - enter context managers
  - exit context managers on container close for scoped and singleton (and values)
  - exit context managers for transient when value is not referenced anymore
- add autowrapping generators into context manager
  - Add ability to disable this as well
- prevent ability to pass enter=False to descriptors when providing a contextmanager or a generator
  - We may also think about handling context managers out of the box or not

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
