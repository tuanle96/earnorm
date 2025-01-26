"""Field validator registry implementation.

This module provides the validator registry for managing field validators.
It supports:
- Validator registration and lookup
- Default validators
- Validator creation
- Validator caching
- Validator configuration

Examples:
    >>> registry = ValidatorRegistry()
    >>> registry.register("min_length", MinLengthValidator)
    >>> validator = registry.create("min_length", min_length=5)
    >>> field = StringField(validators=[validator])
"""

from typing import Any, Callable, Dict, Final, List, Optional, TypeVar, final

from earnorm.fields.validators.base import (
    RangeValidator,
    RegexValidator,
    RequiredValidator,
    TypeValidator,
    Validator,
)
from earnorm.fields.validators.common import DateTimeValidator

T = TypeVar("T")  # Type of value to validate

# Type aliases with better type hints
ValidatorFactory = Callable[..., Validator[Any]]
ValidatorCache = Dict[str, Dict[str, Validator[Any]]]
ValidatorRegistry = Dict[str, ValidatorFactory]


@final
class ValidatorManager:
    """Registry for field validators.

    This class manages validator registration and creation.
    It supports caching of created validators for better performance.

    Attributes:
        _validators: Dictionary mapping validator names to validator factories
        _cache: Cache of created validators
    """

    def __init__(self) -> None:
        """Initialize validator registry."""
        self._validators: ValidatorRegistry = {}
        self._cache: ValidatorCache = {}

    def register(
        self,
        name: str,
        factory: ValidatorFactory,
        cache: bool = True,
    ) -> None:
        """Register validator factory.

        Args:
            name: Name of validator
            factory: Validator factory function
            cache: Whether to cache created validators

        Raises:
            ValueError: If validator name already registered
        """
        if name in self._validators:
            raise ValueError(f"Validator {name} already registered")
        self._validators[name] = factory
        if cache:
            self._cache[name] = {}

    def unregister(self, name: str) -> None:
        """Unregister validator factory.

        Args:
            name: Name of validator to unregister
        """
        self._validators.pop(name, None)
        self._cache.pop(name, None)

    def create(
        self,
        name: str,
        cache_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Validator[Any]:
        """Create validator instance.

        Args:
            name: Name of validator to create
            cache_key: Key for caching validator
            **kwargs: Validator parameters

        Returns:
            Created validator instance

        Raises:
            ValueError: If validator not found
        """
        if name not in self._validators:
            raise ValueError(f"Validator {name} not found")

        # Check cache first
        if cache_key and name in self._cache:
            cached = self._cache[name].get(cache_key)
            if cached is not None:
                return cached

        # Create new validator
        validator = self._validators[name](**kwargs)

        # Cache if requested
        if cache_key and name in self._cache:
            self._cache[name][cache_key] = validator

        return validator

    def clear_cache(self, name: Optional[str] = None) -> None:
        """Clear validator cache.

        Args:
            name: Name of validator to clear cache for, or None for all
        """
        if name is None:
            for cache in self._cache.values():
                cache.clear()
        elif name in self._cache:
            self._cache[name].clear()

    def get_names(self) -> List[str]:
        """Get names of registered validators.

        Returns:
            List of validator names
        """
        return list(self._validators)

    def has_validator(self, name: str) -> bool:
        """Check if validator is registered.

        Args:
            name: Name of validator to check

        Returns:
            True if validator registered, False otherwise
        """
        return name in self._validators


# Create default registry
default_registry: Final[ValidatorManager] = ValidatorManager()

# Register default validators
default_registry.register("required", RequiredValidator)
default_registry.register("type", TypeValidator)
default_registry.register("range", RangeValidator)
default_registry.register("regex", RegexValidator)
default_registry.register("datetime", DateTimeValidator)
