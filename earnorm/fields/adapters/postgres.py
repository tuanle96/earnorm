"""PostgreSQL adapter implementation.

This module provides database adapters for PostgreSQL.
It handles type conversion between Python and PostgreSQL types.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TypeVar, Union, cast
from uuid import UUID

from earnorm.fields.adapters.base import BaseAdapter
from earnorm.fields.types import DatabaseValue

T = TypeVar("T")  # Field value type

# Type aliases for complex types
ScalarValue = Union[str, int, float, bool]
JsonDict = Dict[str, Union[ScalarValue, Dict[str, Any], List[Any]]]
JsonList = List[Union[ScalarValue, Dict[str, Any], List[Any]]]
JsonValue = Union[ScalarValue, JsonDict, JsonList]
ArrayValue = List[Union[ScalarValue, JsonValue]]


class PostgreSQLAdapter(BaseAdapter[T]):
    """PostgreSQL adapter implementation.

    This adapter handles conversion between Python types and PostgreSQL types.
    It supports:
    - Basic types (str, int, float, bool)
    - Complex types (datetime, Decimal, UUID)
    - Array types
    - JSON types
    """

    @property
    def backend_name(self) -> str:
        """Get backend name.

        Returns:
            str: Always returns 'postgresql'
        """
        return "postgresql"

    async def to_db_value(self, value: Optional[T]) -> DatabaseValue:
        """Convert Python value to PostgreSQL type.

        Handles conversion of:
        - None -> NULL
        - str -> VARCHAR/TEXT
        - int -> INTEGER/BIGINT
        - float -> REAL/DOUBLE PRECISION
        - bool -> BOOLEAN
        - datetime -> TIMESTAMP
        - Decimal -> NUMERIC
        - UUID -> UUID
        - list -> ARRAY
        - dict -> JSONB

        Args:
            value: Python value to convert

        Returns:
            DatabaseValue: PostgreSQL value
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
            return value

        # Handle UUID
        if isinstance(value, UUID):
            return str(value)

        # Handle arrays
        if isinstance(value, (list, tuple)):
            # Convert each element to database format
            return [
                str(item) if not isinstance(item, (str, int, float, bool)) else item
                for item in cast(ArrayValue, value)
            ]

        # Handle JSON
        if isinstance(value, dict):
            # Convert values to database format
            json_dict = cast(JsonDict, value)
            return {
                str(k): str(v) if not isinstance(v, ScalarValue) else v
                for k, v in json_dict.items()
            }

        # Default: convert to string
        return str(value)

    async def from_db_value(self, value: DatabaseValue) -> Optional[T]:
        """Convert PostgreSQL type to Python value.

        Handles conversion of:
        - NULL -> None
        - VARCHAR/TEXT -> str
        - INTEGER/BIGINT -> int
        - REAL/DOUBLE PRECISION -> float
        - BOOLEAN -> bool
        - TIMESTAMP -> datetime
        - NUMERIC -> Decimal
        - UUID -> UUID
        - ARRAY -> list
        - JSONB -> dict

        Args:
            value: PostgreSQL value to convert

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

        # Handle Decimal
        if isinstance(value, Decimal):
            return cast(T, value)

        # Handle arrays
        if isinstance(value, list):
            array_value = cast(ArrayValue, value)
            return cast(
                T,
                [
                    str(item) if not isinstance(item, ScalarValue) else item
                    for item in array_value
                ],
            )

        # Handle JSON
        if isinstance(value, dict):
            json_dict = cast(JsonDict, value)
            return cast(
                T,
                {
                    str(k): str(v) if not isinstance(v, ScalarValue) else v
                    for k, v in json_dict.items()
                },
            )

        # Default: convert to string
        return cast(T, str(value))


class PostgresStringAdapter(PostgreSQLAdapter[str]):
    """PostgreSQL adapter for string fields."""

    def __init__(self, max_length: Optional[int] = None) -> None:
        """Initialize string adapter.

        Args:
            max_length: Maximum string length
        """
        field_type = "TEXT" if max_length is None else "VARCHAR"
        super().__init__(field_type, length=max_length)


class PostgresIntAdapter(PostgreSQLAdapter[int]):
    """PostgreSQL adapter for integer fields."""

    def __init__(
        self,
        *,
        small: bool = False,
        big: bool = False,
        auto_increment: bool = False,
    ) -> None:
        """Initialize integer adapter.

        Args:
            small: Use SMALLINT instead of INTEGER
            big: Use BIGINT instead of INTEGER
            auto_increment: Use SERIAL/BIGSERIAL
        """
        if auto_increment:
            if big:
                field_type = "BIGSERIAL"
            else:
                field_type = "SERIAL"
        else:
            if small:
                field_type = "SMALLINT"
            elif big:
                field_type = "BIGINT"
            else:
                field_type = "INTEGER"
        super().__init__(field_type)


class PostgresFloatAdapter(PostgreSQLAdapter[float]):
    """PostgreSQL adapter for float fields."""

    def __init__(self, double_precision: bool = True) -> None:
        """Initialize float adapter.

        Args:
            double_precision: Use DOUBLE PRECISION instead of REAL
        """
        field_type = "DOUBLE PRECISION" if double_precision else "REAL"
        super().__init__(field_type)


class PostgresDecimalAdapter(PostgreSQLAdapter[Decimal]):
    """PostgreSQL adapter for decimal fields."""

    def __init__(self, precision: int, scale: int) -> None:
        """Initialize decimal adapter.

        Args:
            precision: Total number of digits
            scale: Number of decimal places
        """
        super().__init__("NUMERIC", precision=precision, scale=scale)


class PostgresDateTimeAdapter(PostgreSQLAdapter[datetime]):
    """PostgreSQL adapter for datetime fields."""

    def __init__(self, timezone: bool = True) -> None:
        """Initialize datetime adapter.

        Args:
            timezone: Whether to use timezone-aware timestamps
        """
        field_type = "TIMESTAMP WITH TIME ZONE" if timezone else "TIMESTAMP"
        super().__init__(field_type)


class PostgresUUIDAdapter(PostgreSQLAdapter[UUID]):
    """PostgreSQL adapter for UUID fields."""

    def __init__(self) -> None:
        """Initialize UUID adapter."""
        super().__init__("UUID")

    async def to_db_value(self, value: Optional[UUID]) -> DatabaseValue:
        """Convert UUID to string.

        Args:
            value: UUID value

        Returns:
            DatabaseValue: String value
        """
        if value is None:
            return None
        return str(value)

    async def from_db_value(self, value: DatabaseValue) -> Optional[UUID]:
        """Convert string to UUID.

        Args:
            value: String value

        Returns:
            Optional[UUID]: UUID value
        """
        if value is None:
            return None
        return UUID(str(value))


class PostgresJSONAdapter(PostgreSQLAdapter[Dict[str, Any]]):
    """PostgreSQL adapter for JSON fields."""

    def __init__(self, binary: bool = True) -> None:
        """Initialize JSON adapter.

        Args:
            binary: Whether to use JSONB instead of JSON
        """
        field_type = "JSONB" if binary else "JSON"
        super().__init__(field_type)
