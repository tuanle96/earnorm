"""Base module for EarnORM.

This module provides core functionality:
- Model definition and management
- Field types and validation
- Query building and execution
- Record management and operations
- Event handling and lifecycle hooks
"""

from earnorm.base.model import BaseModel
from earnorm.types import FieldProtocol, ModelProtocol

__all__ = [
    "BaseModel",
    "FieldProtocol",
    "ModelProtocol",
]
