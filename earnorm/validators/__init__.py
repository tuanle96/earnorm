"""Validators for EarnORM.

This module provides validators for fields and models, including:
- Base validator classes and exceptions
- Field validators (string, number, composite)
- Model validators (unique, reference, custom)
"""

from earnorm.validators.base import BaseValidator, ValidationError, create_validator
from earnorm.validators.fields.composite import (
    DictSchemaValidator,
    ListItemValidator,
    ListLengthValidator,
    validate_dict_schema,
    validate_list_items,
    validate_list_length,
)
from earnorm.validators.fields.number import (
    RangeValidator,
    validate_max,
    validate_min,
    validate_negative,
    validate_positive,
    validate_range,
    validate_zero,
)
from earnorm.validators.fields.string import (
    EmailValidator,
    IPValidator,
    RegexValidator,
    URLValidator,
    validate_choice,
    validate_length,
    validate_regex,
)
from earnorm.validators.models.custom import (
    AsyncFieldsValidator,
    AsyncModelValidator,
    FieldsValidator,
    ModelValidator,
)
from earnorm.validators.models.reference import ExistsValidator, validate_exists
from earnorm.validators.models.unique import UniqueValidator, validate_unique

__all__ = [
    # Base
    "BaseValidator",
    "ValidationError",
    "create_validator",
    # String validators
    "EmailValidator",
    "IPValidator",
    "RegexValidator",
    "URLValidator",
    "validate_choice",
    "validate_length",
    "validate_regex",
    # Number validators
    "RangeValidator",
    "validate_max",
    "validate_min",
    "validate_negative",
    "validate_positive",
    "validate_zero",
    "validate_range",
    # Composite validators
    "DictSchemaValidator",
    "ListItemValidator",
    "ListLengthValidator",
    "validate_dict_schema",
    "validate_list_items",
    "validate_list_length",
    # Model validators
    "AsyncFieldsValidator",
    "AsyncModelValidator",
    "FieldsValidator",
    "ModelValidator",
    "ExistsValidator",
    "validate_exists",
    "UniqueValidator",
    "validate_unique",
]
