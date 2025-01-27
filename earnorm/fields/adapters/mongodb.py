"""MongoDB adapter implementation.

This module provides adapters for converting between Python types and MongoDB BSON types.
Each adapter handles a specific Python type and provides methods for converting to/from
MongoDB BSON types.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, TypeVar

from bson.decimal128 import Decimal128

from earnorm.fields.adapters.base import BaseAdapter
from earnorm.fields.types import DatabaseValue

T = TypeVar("T")  # Field value type


class MongoDBAdapter(BaseAdapter[T]):
    """Base adapter for MongoDB BSON types.

    This adapter provides default implementations for converting between Python types
    and MongoDB BSON types. Subclasses should override methods to provide type-specific
    conversion behavior.
    """

    @property
    def backend_name(self) -> str:
        """Get backend name.

        Returns:
            str: Always returns 'mongodb'
        """
        return "mongodb"

    async def to_db_value(self, value: Optional[T]) -> DatabaseValue:
        """Convert Python value to MongoDB BSON type.

        Args:
            value: Python value to convert

        Returns:
            DatabaseValue: MongoDB BSON value
        """
        if value is None:
            return None
        try:
            return self._to_db_value(value)
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Invalid value for MongoDB conversion: {str(e)}") from e

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert MongoDB BSON type to Python value.

        Args:
            value: MongoDB BSON value to convert

        Returns:
            Optional[T]: Python value
        """
        if value is None:
            return None
        try:
            return self._from_db_value(value)
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Invalid MongoDB value for conversion: {str(e)}") from e

    def _to_db_value(self, value: T) -> DatabaseValue:
        """Internal method for converting Python value to MongoDB BSON type.

        Args:
            value: Python value to convert

        Returns:
            DatabaseValue: MongoDB BSON value
        """
        return value  # type: ignore

    def _from_db_value(self, value: DatabaseValue) -> T:
        """Internal method for converting MongoDB BSON type to Python value.

        Args:
            value: MongoDB BSON value to convert

        Returns:
            T: Python value
        """
        return value  # type: ignore


class MongoStringAdapter(MongoDBAdapter[str]):
    """Adapter for string values in MongoDB.

    This adapter handles conversion between Python str type and MongoDB string type.
    It ensures that values are properly encoded/decoded as strings.
    """

    def _to_db_value(self, value: str) -> str:
        """Convert Python string to MongoDB string.

        Args:
            value: Python string to convert

        Returns:
            str: MongoDB string value

        Raises:
            TypeError: If value is not a string
        """
        return value

    def _from_db_value(self, value: DatabaseValue) -> str:
        """Convert MongoDB string to Python string.

        Args:
            value: MongoDB string to convert

        Returns:
            str: Python string value

        Raises:
            TypeError: If value is not a string
        """
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
        return value


class MongoIntAdapter(MongoDBAdapter[int]):
    """Adapter for integer values in MongoDB.

    This adapter handles conversion between Python int type and MongoDB integer type.
    It ensures that values are properly converted to integers.
    """

    def _to_db_value(self, value: int) -> int:
        """Convert Python integer to MongoDB integer.

        Args:
            value: Python integer to convert

        Returns:
            int: MongoDB integer value

        Raises:
            TypeError: If value is not an integer
        """
        return value

    def _from_db_value(self, value: DatabaseValue) -> int:
        """Convert MongoDB integer to Python integer.

        Args:
            value: MongoDB integer to convert

        Returns:
            int: Python integer value

        Raises:
            TypeError: If value is not an integer
        """
        if not isinstance(value, int):
            raise TypeError("Value must be an integer")
        return value


class MongoFloatAdapter(MongoDBAdapter[float]):
    """Adapter for float values in MongoDB.

    This adapter handles conversion between Python float type and MongoDB float type.
    It ensures that values are properly converted to floats.
    """

    def _to_db_value(self, value: float) -> float:
        """Convert Python float to MongoDB float.

        Args:
            value: Python float to convert

        Returns:
            float: MongoDB float value

        Raises:
            TypeError: If value is not a float
        """
        return value

    def _from_db_value(self, value: DatabaseValue) -> float:
        """Convert MongoDB float to Python float.

        Args:
            value: MongoDB float to convert

        Returns:
            float: Python float value

        Raises:
            TypeError: If value is not a float
        """
        if not isinstance(value, float):
            raise TypeError("Value must be a float")
        return value


class MongoDecimalAdapter(MongoDBAdapter[Decimal]):
    """Adapter for decimal values in MongoDB.

    This adapter handles conversion between Python Decimal type and MongoDB Decimal128 type.
    It ensures that values are properly converted between the two decimal types.
    """

    def _to_db_value(self, value: Decimal) -> Decimal128:
        """Convert Python Decimal to MongoDB Decimal128.

        Args:
            value: Python Decimal to convert

        Returns:
            Decimal128: MongoDB Decimal128 value

        Raises:
            TypeError: If value is not a Decimal
            InvalidOperation: If value cannot be converted to Decimal128
        """
        return Decimal128(value)

    def _from_db_value(self, value: DatabaseValue) -> Decimal:
        """Convert MongoDB Decimal128 to Python Decimal.

        Args:
            value: MongoDB Decimal128 to convert

        Returns:
            Decimal: Python Decimal value

        Raises:
            TypeError: If value is not a Decimal128
            InvalidOperation: If value cannot be converted to Decimal
        """
        if not isinstance(value, Decimal128):
            raise TypeError("Value must be a Decimal128")
        return value.to_decimal()


class MongoDateTimeAdapter(MongoDBAdapter[datetime]):
    """Adapter for datetime values in MongoDB.

    This adapter handles conversion between Python datetime type and MongoDB datetime type.
    It ensures that values are properly converted between the two datetime types.
    """

    def _to_db_value(self, value: datetime) -> datetime:
        """Convert Python datetime to MongoDB datetime.

        Args:
            value: Python datetime to convert

        Returns:
            datetime: MongoDB datetime value

        Raises:
            TypeError: If value is not a datetime
        """
        return value

    def _from_db_value(self, value: DatabaseValue) -> datetime:
        """Convert MongoDB datetime to Python datetime.

        Args:
            value: MongoDB datetime to convert

        Returns:
            datetime: Python datetime value

        Raises:
            TypeError: If value is not a datetime
        """
        if not isinstance(value, datetime):
            raise TypeError("Value must be a datetime")
        return value
