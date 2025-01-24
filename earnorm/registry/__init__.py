"""Registry module for EarnORM.

This module provides registry management for:
- Models: Model class registration and retrieval
- Databases: Database backend management
- Base: Abstract registry interface

Examples:
    >>> from earnorm.registry import ModelRegistry, DatabaseRegistry
    >>> from earnorm.di import container
    >>>
    >>> # Get model registry
    >>> model_registry = await container.get("model_registry")
    >>> await model_registry.register("User", User)
    >>>
    >>> # Get database registry
    >>> db_registry = await container.get("database_registry")
    >>> await db_registry.register("mongodb", MongoBackend)
"""

from earnorm.registry.base import Registry
from earnorm.registry.database import DatabaseRegistry
from earnorm.registry.model import ModelRegistry

__all__ = ["Registry", "DatabaseRegistry", "ModelRegistry"]
