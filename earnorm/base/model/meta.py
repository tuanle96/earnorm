"""Model metaclass implementation.

This module provides the metaclass for all database models.
It handles:
- Field registration and validation
- Model registration with environment
- Slot creation
- Name generation
- Default fields injection
"""

from datetime import UTC, datetime
from typing import Any, Dict, Set, Type, TypeVar, cast

from earnorm.fields.base import Field
from earnorm.fields.primitive import DateTimeField, StringField


# Forward reference for BaseModel
class BaseModel:
    """Base class for all database models."""

    pass


ValueT = TypeVar("ValueT")


class MetaModel(type):
    """Metaclass for all database models.

    This metaclass handles:
    - Field registration and validation
    - Model registration with environment
    - Slot creation
    - Name generation
    - Default fields injection

    Examples:
        >>> class User(BaseModel):
        ...     name = StringField(required=True)
        ...     email = EmailField(unique=True)
        ...
        >>> user = User(name="John")
        >>> user.id         # Default field
        >>> user.created_at # Default field
        >>> user.updated_at # Default field
    """

    # Define default fields that every model should have
    DEFAULT_FIELDS: Dict[str, Field[Any]] = {
        "id": StringField(
            required=True,
            readonly=True,
            backend_options={"mongodb": {"field_name": "_id"}},  # Map to MongoDB's _id
        ),
        "created_at": DateTimeField(
            required=True, readonly=True, default=lambda: datetime.now(UTC)
        ),
        "updated_at": DateTimeField(
            required=True, readonly=True, default=lambda: datetime.now(UTC)
        ),
    }

    def __new__(
        mcs, name: str, bases: tuple[Type[Any], ...], attrs: Dict[str, Any]
    ) -> Type[BaseModel]:
        """Create new model class.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes

        Returns:
            New model class

        Raises:
            ValueError: If trying to override default field
        """
        # Create slots
        slots: Set[str] = set()
        for base in bases:
            slots.update(getattr(base, "__slots__", ()))

        # Add default fields first
        fields: Dict[str, Field[Any]] = {}
        for field_name, field in mcs.DEFAULT_FIELDS.items():
            # Create a new instance of the field for each model
            new_field = field.__class__(**field.__dict__)
            fields[field_name] = new_field
            new_field.name = field_name
            slots.add(f"_{field_name}")

        # Add user-defined fields
        for key, value in attrs.items():
            if isinstance(value, Field):
                if key in fields:
                    raise ValueError(f"Cannot override default field '{key}'")
                slots.add(f"_{key}")
                fields[key] = value
                value.name = key

        # Add recordset slots
        recordset_slots = {
            "_domain",
            "_limit",
            "_offset",
            "_order",
            "_group_by",
            "_having",
            "_distinct",
            "_env",
            "_data",
            "_changed",
        }
        slots.update(recordset_slots)

        attrs["__slots__"] = tuple(slots)
        attrs["_fields"] = fields

        # Set model name if not defined
        if "_name" not in attrs:
            attrs["_name"] = name.lower()

        # Create new class
        cls = super().__new__(mcs, name, bases, attrs)

        return cast(Type[BaseModel], cls)
