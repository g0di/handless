from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class BindingNotFoundError(HandlessException):
    """Raised when resolving a type that was never bound.

    This typically means:
    - The type was not bound on the container
    - A local scope binding was needed but not provided
    - The type name was misspelled

    When an unbound type is resolved, this exception is raised with a message
    like: "Type <class 'list'> is not bound"

    To fix: Bind the type before resolving it on the container using one of:
    - container.bind(MyType).to_self()
    - container.bind(MyType).to_value(instance)
    - container.bind(MyType).to_factory(factory_func)
    """

    def __init__(self, type_: type[Any]) -> None:
        """Initialize a binding-not-found error.

        :param type_: Missing type that was requested.
        """
        super().__init__(f"Type {type_} is not bound")


class BindingAlreadyExistsError(HandlessException):
    """Raised when attempting to bind a type that's already bound.

    By default, the container prevents duplicate bindings to catch errors.
    This is overridable only via :meth:`Container.override`.

    Example error message: "Type <class 'str'> is already bound"

    To replace a binding:
    - Use :meth:`Container.override` for testing purposes (temporary replacement)
    - Create a new container for a completely fresh setup
    - Use scope-local binding with :meth:`Scope.bind_local` for per-scope changes
    """

    def __init__(self, type_: type[Any]) -> None:
        """Initialize an already-exists binding error.

        :param type_: Type that was already bound.
        """
        super().__init__(f"Type {type_} is already bound")


class BindingError(HandlessException):
    """Raised when an error occurs during type binding.

    This wraps underlying errors that occur during binding, such as:
    - Missing type annotations on factory parameters
    - Invalid factory function signature
    - Conflicting binding settings

    The exception message typically includes details about what went wrong,
    such as: "Cannot bind <Type> using <factory>: <underlying error>"

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
    (e.g., a dependency wasn't bound, or the factory function raised an error).
    """

    def __init__(self, type_: type) -> None:
        """Initialize a resolution error.

        :param type_: Type that failed to resolve.
        """
        super().__init__(f"Cannot resolve {type_}")
