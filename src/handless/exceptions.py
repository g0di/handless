class HandlessException(Exception):
    """Base exception for all handless errors."""


class ContainerException(HandlessException):
    """Base exception for all containers related errors."""


class ServiceNotFoundError(ContainerException):
    """Raised when a service is not found in the container."""

    def __init__(self, service_type: type) -> None:
        super().__init__(f"There is no service {service_type} registered")


class ServiceResolveError(ContainerException):
    """Raised when a service cannot be resolved."""

    def __init__(self, service_type: type) -> None:
        super().__init__(f"Failed resolving {service_type}")
