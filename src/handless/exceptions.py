from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class BindingNotFoundError(HandlessException):
    """When no binding is registered for a given type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is no binding registered for {type_}")


class BindingAlreadyExistingError(HandlessException):
    """When trying to register an already registered type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is already a binding registered for {type_}")


class ResolveError(HandlessException):
    def __init__(self, type_: type) -> None:
        super().__init__(f"An error happenned when resolving {type_}")
