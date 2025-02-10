"""Field types for EarnORM.

This module provides all field types supported by EarnORM:

Base Classes:
    - Field: Base field class
    - ValidationError: Field validation error
    - ValidatorFunc: Validator function type
    - ModelProtocol: Protocol for model types
    - RelationProtocol: Protocol for relation fields
    - FieldProtocol: Protocol for field types

Primitive Fields:
    - StringField: String values
    - IntegerField: Integer numbers
    - FloatField: Floating point numbers
    - BooleanField: Boolean values
    - DateTimeField: Date and time values
    - DateField: Date values
    - DecimalField: Decimal numbers
    - UUIDField: UUID values
    - JSONField: JSON data
    - FileField: File storage
    - EnumField: Enumeration values
    - ObjectIdField: MongoDB ObjectId

Composite Fields:
    - ListField: List of values
    - SetField: Set of unique values
    - DictField: Dictionary/mapping
    - TupleField: Fixed-size tuple
    - EmbeddedField: Nested document

Relation Fields:
    - OneToOneField: One-to-one relationship
    - OneToManyField: One-to-many relationship
    - ManyToOneField: Many-to-one relationship
    - ManyToManyField: Many-to-many relationship

Validators:
    - Validator: Base validator class
    - ValidatorChain: Chain of validators
    - RequiredValidator: Required field validator
    - TypeValidator: Type validation
    - RangeValidator: Value range validation
    - RegexValidator: Pattern matching
    - MinLengthValidator: Minimum length
    - MaxLengthValidator: Maximum length
    - EmailValidator: Email format
    - URLValidator: URL format
    - UniqueValidator: Unique values

"""

# Exceptions
from earnorm.exceptions import (
    FieldError,
    FieldValidationError,
    ModelNotFoundError,
    ModelResolutionError,
)

# Base classes
from earnorm.fields.base import BaseField

# Composite fields
from earnorm.fields.composite import (
    DictField,
    EmbeddedField,
    ListField,
    SetField,
    TupleField,
)

# Primitive fields
from earnorm.fields.primitive import BooleanField, DateField
from earnorm.fields.primitive import DateTimeField
from earnorm.fields.primitive import DateTimeField as DatetimeField
from earnorm.fields.primitive import (
    DecimalField,
    EnumField,
    FileField,
    FloatField,
    IntegerField,
    JSONField,
    ObjectIdField,
    StringField,
    TimeField,
    UUIDField,
)

# Relation fields
from earnorm.fields.relations import (
    ManyToManyField,
    ManyToOneField,
    OneToManyField,
    OneToOneField,
    RelationField,
)

# Validators
from earnorm.fields.validators.base import (
    RangeValidator,
    RegexValidator,
    RequiredValidator,
    TypeValidator,
    Validator,
    ValidatorChain,
)
from earnorm.fields.validators.common import (
    EmailValidator,
    MaxLengthValidator,
    MinLengthValidator,
    UniqueValidator,
    URLValidator,
)

# Types
from earnorm.types.fields import FieldProtocol, RelationProtocol

# Relation fields


__all__ = [
    # Base classes
    "BaseField",
    "RelationProtocol",
    "FieldProtocol",
    # Primitive fields
    "StringField",
    "IntegerField",
    "FloatField",
    "BooleanField",
    "DateField",
    "TimeField",
    "DateTimeField",
    "DatetimeField",
    "DecimalField",
    "UUIDField",
    "JSONField",
    "FileField",
    "EnumField",
    "ObjectIdField",
    # Composite fields
    "ListField",
    "SetField",
    "DictField",
    "TupleField",
    "EmbeddedField",
    # Relation fields
    "ManyToManyField",
    "ManyToOneField",
    "OneToManyField",
    "OneToOneField",
    "RelationField",
    # Validators
    "Validator",
    "ValidatorChain",
    "RequiredValidator",
    "TypeValidator",
    "RangeValidator",
    "RegexValidator",
    "MinLengthValidator",
    "MaxLengthValidator",
    "EmailValidator",
    "URLValidator",
    "UniqueValidator",
    # Exceptions
    "FieldError",
    "FieldValidationError",
    "ModelNotFoundError",
    "ModelResolutionError",
]
