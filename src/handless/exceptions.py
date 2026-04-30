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

    The exception message includes the full dependency chain that led to the
    failure, from the outermost requested type to the type that actually failed,
    followed by a description of the root cause.

    Access :attr:`outer_type` to get the outermost requested type (i.e. the
    type the caller asked to resolve).
    Access :attr:`inner_type` to get the innermost failing type.
    Access :attr:`resolution_chain` to see each type in the resolution path,
    from outermost to innermost (the type whose factory actually raised).
    Access :attr:`root_cause` or ``__cause__`` to inspect the original
    exception that actually broke resolution.
    """

    def __init__(self, outer_type: type[Any]) -> None:
        """Initialize a resolution error.

        :param outer_type: Type whose resolution directly triggered this error.
        """
        super().__init__()
        self._chain: list[type[Any]] = [outer_type]

    @property
    def outer_type(self) -> type[Any]:
        """Type originally resolved by the caller (outermost in the chain)."""
        return self.resolution_chain[0]

    @property
    def inner_type(self) -> type[Any]:
        """Type whose resolution actually failed (innermost in the chain)."""
        return self.resolution_chain[-1]

    @property
    def resolution_chain(self) -> tuple[type[Any], ...]:
        """Resolution path from outermost to innermost (failing) type.

        The first element is the type originally resolved by the caller; the last element
        is the type whose resolution actually failed.
        """
        return tuple(reversed(self._chain))

    def add_parent_resolved_type(self, parent_type: type[Any]) -> None:
        self._chain.append(parent_type)

    @property
    def root_cause(self) -> BaseException | None:
        """Underlying exception that actually caused the resolution failure."""
        return self.__cause__

    def __str__(self) -> str:
        resolution_chain_str = "\n".join(
            [
                "  Resolution chain (outermost type first):",
                *(f"    -> {t}" for t in self.resolution_chain[:-1]),
                f"    !! {self.inner_type}: {self.root_cause}",
            ]
        )
        return f"Cannot resolve {self.outer_type}:\n{resolution_chain_str}"

    def __repr__(self) -> str:
        return (
            f"ResolutionError(outer_type={self.outer_type!r}, "
            f"inner_type={self.inner_type!r}, "
            f"resolution_chain={self.resolution_chain}, "
            f"root_cause={self.root_cause!r})"
        )
