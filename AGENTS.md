# handless - Dependency injection library for Python

Handless is a python library providing a dependency injection container to facilitates building and composing object graphs for Python applications.
It is designed to simplify the burden of manually wiring dependencies and managing various object lifetimes (singleton, scoped, transient).
The main motivation behind this library is mostly to fill gaps found on existing ones. There is several existing libraries already (lagom, svcs, dependency_injector, ...) but they all have some caveats:

- Type checking: they don't verify that values, functions or types registered are of the right type
- Singleton management: some library does not allows to have singleton to keep same values for an application lifetime
- Hard to replace for testing purposes: no easy mechanism is provided to temporarily override a dependency in a container for tests duration

Current implementation provides an imperative API for building a container and resolving objects from it.
This library tries to follow dependency injection best practices and patterns:

- **Composition root**: the mapping between concrete classes and interface must be composed as close as possible to the application entry point. The Composition root should be an unique location in the application;
- **Register, Resolve, Release**: The Register, Resolve and Release pattern describes how to use a DI container. The Register Resolve Release pattern states that a DI Container’s methods must be invoked in this strict sequence. The Register method register components with container. The Resolve method resolves the concrete class basing on an interface. Finally, Release method destroys the instances when they are no longer needed;

This library currently support the following injection method:

- **Constructor injection**
- **Method injection**

## Directory structure

- `src/`: Source code
  - `handless/`: Package root
    - `_container.py`: DI Container and context/scope source code. Allows to register types and their implementations, create context/scope for resolving objects and hold singletons
    - `_registry.py`: Registry for binding types to concrete implementations. Used behind the scene by the container
    - `_utils.py`: Various utility functions
    - `exceptions.py`: Public exceptions raise by the library
    - `lifetimes.py`: The various lifetimes for registering objects in a container. It handles how objects are resolved, when it is cached and released.
- `tests/`: All tests
  - `test_register.py`: All tests about registering types and implementation on a container and, indirectly, a registry
  - `test_resolve.py`: All tests on resolving objects from containers and context/scope. Verify lifetimes, caching, context management
  - `test_resolve_async.py`: Literally the async version of tests in `test_resolve.py`, using async functions of container and context/scope. Must be kept in sync with `test_resolve.py`

## Build and test commands

- `uv sync`: Setup project virtual environment and install/update required dependencies
- `uv run nox`: Reformat all Python code and imports, run linter and safe fixes, type checking and finally run all tests on many python versions
- `uv run ruff format`: Reformat all Python code
- `uv run ruff check --fix --show-fixes --output-format json --statistics`: Reformat Python imports, lint Python code, apply safe fixes and output JSON report
- `uv run mypy -O json`: Run Python type checking and output JSON report
- `uv run nox -s test`: Run tests and compute coverage for many Python versions

## Code style guidelines

- Ensure everything is properly typed and have type annotations
- Public functions and classes are documented using docstrings
  - It starts with a summary line
  - Provide more details and information in the docstring body
  - Include doctest examples
  - Use pep257 and sphinx style for docstrings
  - Document raises errors and parameters
  - Documents returned value only if it is not just `None`
- Limit library public API to only what we want to provide to users. Internals should be marked as private:
  - Private packages are prefixed with an underscore
  - Private objects in public packages are prefixed with underscore
  - Private methods or attributes part of public objects are prefixed with an underscore
  - In case of doubts default to private visibility for new code if it is not clear that this is part of the public API
- Boolean flags (boolean method arguments must be keyword arguments only)

## Testing instructions

- Code coverage must be as close as possible to 100%. If not try to fill the gap with new tests
- Tests must pass on all python versions starting from 3.10
- Tests must cover both sync and async code. The library supports both so earch tests must be duplicated and synced.
- Tests should focus on the public facing API rather than testing internals
- Any new feature or bug fixes must be covered by a test beforehand
  - The test is written first to validate the behavior then the code is implemented (test-first)
- Tests covering a same method should be grouped under a same class for readability
- Use pytest.mark.parametrize to test a same function with different inputs and outputs rather than creating one per situation

## Security considerations

- Particular care must be taken to avoid memory leak when managing dependencies and their lifetime with containers and contexts
  - Closing a container context/scope must always close all objects entered
  - Closing a container must always close all objects entered

## Contributing

- Each notable changes made must be added in the unreleased section [CHANGELOG.md](./CHANGELOG.md) file following [keepachangelog](https://keepachangelog.com/en/1.1.0/) recommendations
  - Purely internal changes must be kept concise on a dedicated internal section
  - Previous changelog entries (released versions) must not be updated during refactoring operations except explicitly asked for
- Documentation wether on code docstring or [README.md](./README.md) must be kept synced with the code.
  - New features must be added to the documentation
- After changes, update the [TODO.md](./TODO.md) to remove occurences of the change
