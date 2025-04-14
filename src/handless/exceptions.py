from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class RegistrationNotFoundError(HandlessException):
    """When there is no provider registered for a given type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is no provider registered for {type_}")


class RegistrationAlreadyExistingError(HandlessException):
    """When trying to register an already registered type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is already a provider registered for {type_}")


class ResolveError(HandlessException):
    def __init__(self, type_: type) -> None:
        super().__init__(f"An error happenned when resolving {type_}")
