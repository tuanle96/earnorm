"""EarnORM - High-performance async-first MongoDB ORM for Python.

This module provides a high-performance, async-first MongoDB ORM with features like:
- Async/await support
- Type safety with Pydantic
- Computed fields and field validation
- Record rules and access control
- Caching and audit logging
- Dependency injection
"""

from earnorm.app import EarnORMApp
from earnorm.base import fields
from earnorm.base.model import BaseModel
from earnorm.base.registry import env
from earnorm.di.container import container

__version__ = "0.1.0"

__all__ = [
    "BaseModel",
    "env",
    "fields",
    "container",
    "EarnORMApp",
]
