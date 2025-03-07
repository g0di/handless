class HandlessException(Exception):
    """Base exception for all handless errors."""


class RegistryException(Exception):
    """Base exception for all registry related errors."""


class RegistrationError(RegistryException):
    """When a service registration failed."""


class ContainerException(Exception):
    """Base exception for all containers related errors."""


class ServiceNotFoundError(ContainerException):
    def __init__(self, service_type: type) -> None:
        super().__init__(f"There is no service {service_type} registered")


class ServiceResolveError(ContainerException):
    def __init__(self, service_type: type, reason: str) -> None:
        super().__init__(f"Failed resolving {service_type}: {reason}")
