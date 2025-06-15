import logging
from typing import Any, TypeVar

from typing_extensions import Self

from handless._bindings import Binding
from handless.exceptions import RegistrationAlreadyExistError

_T = TypeVar("_T")


class Registry:
    """Map object types to their binding."""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._bindings: dict[type[Any], Binding[Any]] = {}

    def register(self, binding: Binding[Any]) -> Self:
        if binding.type_ in self._bindings:
            raise RegistrationAlreadyExistError(binding.type_)

        self._bindings[binding.type_] = binding
        self._logger.info("Registered %s: %s", binding.type_, binding)
        return self

    def get_binding(self, type_: type[_T]) -> Binding[_T] | None:
        return self._bindings.get(type_)
