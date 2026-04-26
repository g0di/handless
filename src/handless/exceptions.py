from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class RegistrationNotFoundError(HandlessException):
    """Raised when resolving a type that was never registered.

    This typically means:
    - The type was not registered on the container
    - A local scope registration was needed but not provided
    - The type name was misspelled

    When an unregistered type is resolved, this exception is raised with a message
    like: "Type <class 'list'> is not registered"

    To fix: Register the type before resolving it on the container using one of:
    - container.register(MyType).self()
    - container.register(MyType).value(instance)
    - container.register(MyType).factory(factory_func)
    """

    def __init__(self, type_: type[Any]) -> None:
        """Initialize a registration-not-found error.

        :param type_: Missing type that was requested.
        """
        super().__init__(f"Type {type_} is not registered")


class RegistrationAlreadyExistError(HandlessException):
    """Raised when attempting to register a type that's already registered.

    By default, the container prevents duplicate registrations to catch errors.
    This is overridable only via :meth:`Container.override`.

    Example error message: "Type <class 'str'> is already registered"

    To replace a registration:
    - Use :meth:`Container.override` for testing purposes (temporary replacement)
    - Create a new container for a completely fresh setup
    - Use scope-local registration with :meth:`Scope.register_local` for per-scope changes
    """

    def __init__(self, type_: type[Any]) -> None:
        """Initialize an already-exists registration error.

        :param type_: Type that was already registered.
        """
        super().__init__(f"Type {type_} is already registered")


class RegistrationError(HandlessException):
    """Raised when an error occurs during type registration.

    This wraps underlying errors that occur during registration, such as:
    - Missing type annotations on factory parameters
    - Invalid factory function signature
    - Conflicting registration settings

    The exception message typically includes details about what went wrong,
    such as: "Cannot register <Type> using <factory>: <underlying error>"

    Ensure all factory function parameters have type annotations for proper
    dependency injection, or use a single untyped parameter to receive a Scope.
    """


class ResolutionError(HandlessException):
    """Raised when an error occurs while resolving a type.

    This wraps the underlying exception that occurred during factory execution,
    such as:
    - Missing or unresolvable dependencies
    - Factory function raised an exception
    - Type annotation mismatches

    The exception message indicates which type failed to resolve, for example:
    "Cannot resolve <class 'Service'>"

    Access the ``__cause__`` attribute to see the original exception that caused
    the resolution to fail. This usually contains more details about what went wrong
    (e.g., a dependency wasn't registered, or the factory function raised an error).
    """

    def __init__(self, type_: type) -> None:
        """Initialize a resolution error.

        :param type_: Type that failed to resolve.
        """
        super().__init__(f"Cannot resolve {type_}")
