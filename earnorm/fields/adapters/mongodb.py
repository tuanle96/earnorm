"""MongoDB adapter implementation.

This module provides database adapters for MongoDB.
It handles type conversion between Python and MongoDB BSON types.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TypeVar, cast

from bson import ObjectId
from bson.decimal128 import Decimal128

from earnorm.fields.adapters.base import BaseAdapter
from earnorm.fields.types import DatabaseValue

T = TypeVar("T")  # Field value type


class MongoDBAdapter(BaseAdapter[T]):
    """MongoDB adapter implementation.

    This adapter handles conversion between Python types and MongoDB BSON types.
    It supports:
    - Basic types (str, int, float, bool)
    - Complex types (datetime, Decimal, ObjectId)
    - Custom type conversions
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

        Handles conversion of:
        - None -> None
        - str -> str
        - int -> int
        - float -> float
        - bool -> bool
        - datetime -> datetime
        - Decimal -> Decimal128
        - ObjectId -> ObjectId

        Args:
            value: Python value to convert

        Returns:
            DatabaseValue: MongoDB BSON value
        """
        if value is None:
            return None

        # Handle basic types
        if isinstance(value, (str, int, float, bool)):
            return value

        # Handle datetime
        if isinstance(value, datetime):
            return value

        # Handle Decimal
        if isinstance(value, Decimal):
            return Decimal128(value)

        # Handle ObjectId
        if isinstance(value, ObjectId):
            return value

        # Default: convert to string
        return str(value)

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert MongoDB BSON type to Python value.

        Handles conversion of:
        - None -> None
        - str -> str
        - int -> int
        - float -> float
        - bool -> bool
        - datetime -> datetime
        - Decimal128 -> Decimal
        - ObjectId -> ObjectId

        Args:
            value: MongoDB BSON value to convert

        Returns:
            Optional[T]: Python value
        """
        if value is None:
            return None

        # Handle basic types
        if isinstance(value, (str, int, float, bool)):
            return cast(T, value)

        # Handle datetime
        if isinstance(value, datetime):
            return cast(T, value)

        # Handle Decimal128
        if isinstance(value, Decimal128):
            return cast(T, Decimal(str(value)))

        # Handle ObjectId
        if isinstance(value, ObjectId):
            return cast(T, value)

        # Default: convert to string
        return cast(T, str(value))


class MongoStringAdapter(MongoDBAdapter[str]):
    """MongoDB adapter for string fields."""

    def __init__(self, max_length: Optional[int] = None) -> None:
        """Initialize string adapter.

        Args:
            max_length: Maximum string length
        """
        field_options = {"maxLength": max_length} if max_length is not None else {}
        super().__init__(field_type="string", **field_options)


class MongoIntAdapter(MongoDBAdapter[int]):
    """MongoDB adapter for integer fields."""

    def __init__(
        self,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> None:
        """Initialize integer adapter.

        Args:
            min_value: Minimum value
            max_value: Maximum value
        """
        field_options = {}
        if min_value is not None:
            field_options["min"] = min_value
        if max_value is not None:
            field_options["max"] = max_value

        super().__init__(field_type="int", **field_options)


class MongoFloatAdapter(MongoDBAdapter[float]):
    """MongoDB adapter for float fields."""

    def __init__(self, precision: Optional[int] = None) -> None:
        """Initialize float adapter.

        Args:
            precision: Decimal precision
        """
        field_options = {"precision": precision} if precision is not None else {}
        super().__init__(field_type="double", **field_options)


class MongoDecimalAdapter(MongoDBAdapter[Decimal]):
    """MongoDB adapter for decimal fields."""

    def __init__(self, precision: int, scale: int) -> None:
        """Initialize decimal adapter.

        Args:
            precision: Total number of digits
            scale: Number of decimal places
        """
        super().__init__(
            field_type="decimal",
            precision=precision,
            scale=scale,
        )

    async def to_db_value(self, value: Optional[Decimal]) -> DatabaseValue:
        """Convert Decimal to Decimal128.

        Args:
            value: Decimal value

        Returns:
            DatabaseValue: Decimal128 value
        """
        if value is None:
            return None
        return Decimal128(value)

    async def from_db_value(self, value: DatabaseValue) -> Optional[Decimal]:
        """Convert Decimal128 to Decimal.

        Args:
            value: Decimal128 value

        Returns:
            Optional[Decimal]: Decimal value
        """
        if value is None:
            return None
        if isinstance(value, Decimal128):
            return Decimal(str(value))
        return Decimal(str(value))


class MongoDateTimeAdapter(MongoDBAdapter[datetime]):
    """MongoDB adapter for datetime fields."""

    def __init__(self, timezone: bool = True) -> None:
        """Initialize datetime adapter.

        Args:
            timezone: Whether to use timezone-aware datetimes
        """
        super().__init__(field_type="date", timezone=timezone)
