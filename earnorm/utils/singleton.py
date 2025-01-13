"""Singleton metaclass implementation."""

from typing import Any, Dict, Type


class Singleton(type):
    """Metaclass for singleton pattern."""

    _instances: Dict[Type[Any], Any] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Create or return singleton instance."""
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
