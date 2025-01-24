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

Events:
    - EventEmitter: Base event emitter
    - EventBus: Event dispatcher
    - EventType: Event type enum
    - FieldEvent: Event data container
    - EventHandler: Event handler type
    - LoggingHandler: Event logging
    - ChangeTracker: Change tracking
    - ValidationHandler: Validation handling
    - CleanupHandler: Resource cleanup
"""

# Base classes
from earnorm.fields.base import Field, ValidationError

# Composite fields
from earnorm.fields.composite import (
    DictField,
    EmbeddedField,
    ListField,
    SetField,
    TupleField,
)

# Events
from earnorm.fields.events import (
    ChangeTracker,
    CleanupHandler,
    EventBus,
    EventEmitter,
    EventHandler,
    EventType,
    FieldEvent,
    LoggingHandler,
    ValidationHandler,
)

# Primitive fields
from earnorm.fields.primitive import (
    BooleanField,
    DateTimeField,
    DecimalField,
    EnumField,
    FileField,
    FloatField,
    IntegerField,
    JSONField,
    ObjectIdField,
    StringField,
    UUIDField,
)

# Relation fields
from earnorm.fields.relation import (
    ManyToManyField,
    ManyToOneField,
    OneToManyField,
    OneToOneField,
)
from earnorm.fields.types import FieldProtocol, RelationProtocol, ValidatorFunc

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

__all__ = [
    # Base classes
    "Field",
    "ValidationError",
    "ValidatorFunc",
    "RelationProtocol",
    "FieldProtocol",
    # Primitive fields
    "StringField",
    "IntegerField",
    "FloatField",
    "BooleanField",
    "DateTimeField",
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
    "OneToOneField",
    "OneToManyField",
    "ManyToOneField",
    "ManyToManyField",
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
    # Events
    "EventEmitter",
    "EventBus",
    "EventType",
    "FieldEvent",
    "EventHandler",
    "LoggingHandler",
    "ChangeTracker",
    "ValidationHandler",
    "CleanupHandler",
]
