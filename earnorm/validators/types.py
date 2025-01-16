"""Validator types."""

from typing import Any, Callable, TypeAlias

# Type for validator functions
ValidatorFunc: TypeAlias = Callable[[Any], None]
