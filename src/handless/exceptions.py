from typing import Any


class HandlessException(Exception):  # noqa: N818
    """Base exception for all handless errors."""


class RegistrationNotFoundError(HandlessException):
    """When the given type has not been registered on the container."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"Type {type_} is not registered")


class RegistrationAlreadyExistError(HandlessException):
    """When trying to register an already registered type."""

    def __init__(self, type_: type[Any]) -> None:
        super().__init__(f"Type {type_} is already registered")


class RegistrationError(HandlessException):
    """When an error happen while registering a type."""


class ResolutionError(HandlessException):
    """When an error happen during resolution of a type."""

    def __init__(self, type_: type) -> None:
        super().__init__(f"Cannot resolve {type_}")
