"""ObjectId field type.

This module provides the ObjectIdField class for handling MongoDB ObjectId values.
It supports:
- ObjectId validation and conversion
- String/value conversion to ObjectId
- Auto-generation of new ObjectIds
- Database backend support

Examples:
    >>> class User(Model):
    ...     id = ObjectIdField(primary_key=True)
    ...     ref_id = ObjectIdField(required=True)

    >>> user = User()
    >>> user.id  # Auto-generated ObjectId
    >>> user.ref_id = "507f1f77bcf86cd799439011"  # String conversion
    >>> user.ref_id = ObjectId()  # Direct ObjectId assignment
"""

from typing import Any, Optional, Type, Union

from bson import ObjectId
from bson.errors import InvalidId

from earnorm.fields.base import Field, ValidationError


class ObjectIdField(Field[ObjectId]):
    """ObjectId field for MongoDB document IDs.

    This field handles:
    - ObjectId validation and conversion
    - Auto-generation of new ObjectIds
    - String conversion to ObjectId
    - Database serialization

    Attributes:
        required: Whether field is required
        unique: Whether field value must be unique
        primary_key: Whether field is primary key

    Raises:
        ValidationError: With codes:
            - invalid_type: Value cannot be converted to ObjectId
            - invalid_format: Value has invalid ObjectId format
    """

    def _get_field_type(self) -> Type[ObjectId]:
        """Get field type.

        Returns:
            ObjectId type
        """
        return ObjectId

    async def convert(self, value: Any) -> ObjectId:
        """Convert value to ObjectId.

        Args:
            value: Value to convert (None, str, or ObjectId)

        Returns:
            Converted ObjectId value

        Raises:
            ValidationError: With codes:
                - invalid_type: Value cannot be converted to ObjectId
                - invalid_format: Value has invalid ObjectId format

        Examples:
            >>> field = ObjectIdField()
            >>> await field.convert(None)  # Returns new ObjectId
            >>> await field.convert("507f1f77bcf86cd799439011")  # Returns ObjectId
            >>> await field.convert(ObjectId())  # Returns as is
        """
        if value is None or value == "":
            return ObjectId()  # Generate new ObjectId

        if isinstance(value, ObjectId):
            return value

        try:
            return ObjectId(str(value))
        except (TypeError, InvalidId) as e:
            raise ValidationError(
                message=f"Invalid ObjectId format: {value}",
                field_name=self.name,
                code="invalid_format",
            ) from e

    async def to_db(
        self, value: Optional[ObjectId], backend: str
    ) -> Optional[Union[str, ObjectId]]:
        """Convert ObjectId for database storage.

        Args:
            value: ObjectId value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            String (SQL) or ObjectId (MongoDB) or None

        Examples:
            >>> field = ObjectIdField()
            >>> await field.to_db(ObjectId(), "mongodb")  # Returns ObjectId
            >>> await field.to_db(ObjectId(), "postgres")  # Returns str
            >>> await field.to_db(None, "mysql")  # Returns None
        """
        if value is None:
            return None

        if backend == "mongodb":
            return value
        return str(value)

    async def from_db(self, value: Any, backend: str) -> ObjectId:
        """Convert database value to ObjectId.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted ObjectId value

        Raises:
            ValidationError: With codes:
                - invalid_type: Value cannot be converted to ObjectId
                - invalid_format: Value has invalid ObjectId format

        Examples:
            >>> field = ObjectIdField()
            >>> await field.from_db(ObjectId(), "mongodb")  # Returns as is
            >>> await field.from_db("507f1f77bcf86cd799439011", "postgres")  # Converts
            >>> await field.from_db(None, "mysql")  # Returns new ObjectId
        """
        if value is None:
            return ObjectId()

        if isinstance(value, ObjectId):
            return value

        try:
            return ObjectId(str(value))
        except (TypeError, InvalidId) as e:
            raise ValidationError(
                message=f"Invalid ObjectId format in database: {value}",
                field_name=self.name,
                code="invalid_format",
            ) from e
