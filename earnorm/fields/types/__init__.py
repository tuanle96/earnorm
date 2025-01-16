"""Type definitions for fields."""

from typing import Any, Callable, Dict, List, TypeVar, Union

from bson import ObjectId

# Type for field values
FieldValue = Union[
    None,
    bool,
    int,
    float,
    str,
    ObjectId,
    List[Any],
    Dict[str, Any],
]

# Type for validator functions
ValidatorFunc = Callable[[Any], None]

# Type variable for field types
T = TypeVar("T")

# Type for field options
FieldOptions = Dict[str, Any]

# Type for field metadata
FieldMetadata = Dict[str, Any]

# Type for field conversion result
ConversionResult = Union[
    None, bool, int, float, str, ObjectId, List[Any], Dict[str, Any]
]

__all__ = [
    "FieldValue",
    "ValidatorFunc",
    "T",
    "FieldOptions",
    "FieldMetadata",
    "ConversionResult",
]
