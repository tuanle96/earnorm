"""Registry module for managing model registries.

This module provides base classes and implementations for model registries.

Examples:
    >>> from earnorm.registry import ModelRegistry
    >>> from earnorm.di import container
    >>>
    >>> # Get model registry
    >>> model_registry = await container.get("model_registry")
    >>> await model_registry.register("User", User)
"""

from .base import Registry
from .model import ModelLifecycle, ModelRegistry

__all__ = ["Registry", "ModelRegistry", "ModelLifecycle"]
