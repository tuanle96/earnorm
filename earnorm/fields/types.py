"""Field types and validation context.

This module provides type definitions for field validation.
"""

from dataclasses import dataclass, field as dataclass_field
from typing import Any, Protocol


class EnvironmentProtocol(Protocol):
    """Protocol for environment interface."""

    pass


class ModelProtocol(Protocol):
    """Protocol for model interface."""

    pass


class FieldProtocol(Protocol):
    """Protocol for field interface."""

    pass


@dataclass
class ValidationContext:
    """Validation context for field validation.

    This class provides context information for field validation:
    - field: Field being validated
    - value: Value being validated
    - model: Model instance
    - env: Environment instance
    - operation: Operation type (create/write/search...)
    - values: All values being validated
    """

    field: FieldProtocol
    value: Any | None = None
    model: ModelProtocol | None = None
    env: EnvironmentProtocol | None = None
    operation: str | None = None
    values: dict[str, Any] = dataclass_field(default_factory=dict)
