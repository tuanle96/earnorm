"""Type definitions for EarnORM.

This module provides all type definitions used throughout EarnORM.
"""

# Base types
from .base import DomainOperator, JsonDict, JsonValue, ValueType

# Database types
from .database import DatabaseProtocol

# Field types
from .fields import (
    BackendOptions,
    ComparisonOperator,
    ComputeMethod,
    DatabaseValue,
    FieldComparisonMixin,
    FieldDependencies,
    FieldOptions,
    FieldProtocol,
    FieldValue,
    RelationProtocol,
    ValidatorCallable,
    ValidatorFunc,
    ValidatorProtocol,
    ValidatorResult,
)

# Model types
from .models import DatabaseModel, FieldName, ModelName, ModelProtocol, RecordID

__all__ = (
    # Base types
    "JsonValue",
    "JsonDict",
    "DomainOperator",
    "ValueType",
    # Field types
    "FieldValue",
    "FieldOptions",
    "ComputeMethod",
    "FieldDependencies",
    "ValidatorFunc",
    "DatabaseValue",
    "BackendOptions",
    "ValidatorResult",
    "ValidatorCallable",
    "FieldComparisonMixin",
    "ValidatorProtocol",
    "FieldProtocol",
    "RelationProtocol",
    "ComparisonOperator",
    # Model types
    "ModelName",
    "FieldName",
    "RecordID",
    "ModelProtocol",
    "DatabaseModel",
    # Database types
    "DatabaseProtocol",
)
