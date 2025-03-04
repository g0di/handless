- remove ability to pass lifetime to factory registration
- think of renaming register with add to improve readability and reduce amount of characters to type
- think of adding service type in service descriptor (if this makes any sense)
- think of using a specific descriptor for values?
- think of removing the value registration and merge it with singleton?

## Context management

- add handling of context managers
  - enter context managers
  - exit context managers on container close for scoped and singleton (and values)
  - exit context managers for transient when value is not referenced anymore
- add autowrapping generators into context manager
  - Add ability to disable this as well
- prevent ability to pass enter=False to descriptors when providing a contextmanager or a generator
  - We may also think about handling context managers out of the box or not

## Resolving

- add possibility to autowire (resolving dependencies not registered in the container)

## Async

- add handling of async factories
- add handling of async context managers

## Misc

- add resolve stack for debugging
- handle resolving singleton from different threads
- add function for resolving all services in container for testing purposes
- add function for verifying scopes validities at registration time
- add log messages/dev warnings when there is scopes mismatches
- add docstrings
- add function for registering many services in one call in the registry
  - We may also add a function for updating one registry with another

## Testing

- add ability to copy registry/containers for testing purposes
- add ability to temporarily override container/registry for testing purposes
