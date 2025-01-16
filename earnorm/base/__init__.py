"""Base module for EarnORM.

This module provides core functionality:
- Model definition and management
- Field types and validation
- Query building and execution
- Record management and operations
- Event handling and lifecycle hooks
"""

from earnorm.base.model import BaseModel
from earnorm.base.types import (
    ContainerProtocol,
    DocumentType,
    FieldProtocol,
    ModelProtocol,
    RecordSetProtocol,
    RegistryProtocol,
)

__all__ = [
    "BaseModel",
    "ContainerProtocol",
    "DocumentType",
    "FieldProtocol",
    "ModelProtocol",
    "RecordSetProtocol",
    "RegistryProtocol",
]
