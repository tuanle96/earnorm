"""Field type definitions.

This module provides common type definitions used across field implementations.
It includes:
- Validation types
- Field metadata types
- Common type aliases
"""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Dict, Tuple, TypeVar, Union

# Type variables
T = TypeVar("T")  # Field value type

# Type aliases
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidationMetadata = Dict[str, Any]


@dataclass(frozen=True)
class ValidationContext:
    """Context for validation.

    This class provides context information for validation, including:
    - The field being validated
    - The value being validated
    - Additional metadata for validation

    Attributes:
        field: Field being validated
        value: Value being validated
        metadata: Additional validation metadata
    """

    field: Any  # Avoid circular import by using Any
    value: Any
    metadata: ValidationMetadata = dataclass_field(default_factory=dict)
