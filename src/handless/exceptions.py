class HandlessException(Exception):
    """Base exception for all handless errors."""


class ProviderNotFoundError(HandlessException):
    """When no provider is registered for a given type."""

    def __init__(self, type_: type) -> None:
        super().__init__(f"There is no provider registered for {type_}")


class ResolveError(HandlessException):
    def __init__(self, type_: type) -> None:
        super().__init__(f"An error happenned when resolving {type_}")
