from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class RegistrationNotFoundError(HandlessException):
    """When the given type has not been registered on the container."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is no binding registered for {type_}")


class RegistrationAlreadyExistError(HandlessException):
    """When trying to register an already registered type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"There is already a binding registered for {type_}")


class ResolutionError(HandlessException):
    def __init__(self, type_: type) -> None:
        super().__init__(f"An error happenned when resolving {type_}")
