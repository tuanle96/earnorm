"""JSON serializer implementation.

This module provides JSON serializer implementation that uses standard json module
with custom encoder for datetime objects.

Examples:
    ```python
    from earnorm.cache.serializers.json import JsonSerializer

    # Create serializer
    serializer = JsonSerializer()

    # Serialize value with datetime
    from datetime import datetime
    value = {
        "name": "John",
        "created_at": datetime.now()
    }
    serialized = serializer.dumps(value)
    print(serialized)  # {"created_at":"2024-02-04T17:23:17.443Z","name":"John"}

    # Deserialize value
    deserialized = serializer.loads(serialized)
    print(deserialized)  # {"name": "John", "created_at": datetime.datetime(...)}
    ```
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from bson import ObjectId

from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.exceptions import SerializationError

logger = logging.getLogger(__name__)

# Define more specific types
JsonPrimitive = Union[str, int, float, bool, None]
JsonDict = Dict[str, Any]
JsonList = List[Union[JsonDict, JsonPrimitive]]
JsonValue = Union[JsonDict, JsonList, JsonPrimitive]


class MongoJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder with datetime and MongoDB ObjectId support.

    This encoder converts:
    - datetime objects to ISO format strings
    - ObjectId to string
    for JSON serialization.
    """

    def default(self, o: Any) -> Any:
        """Convert datetime objects to ISO format strings and ObjectId to string.

        Args:
            o: Object to encode

        Returns:
            str: ISO format string for datetime objects or string for ObjectId
            Any: Original object for other types

        Examples:
            ```python
            encoder = MongoJsonEncoder()
            now = datetime.now()
            id = ObjectId()
            encoded = encoder.encode({"time": now, "id": id})
            print(encoded)  # {"time": "2024-02-04T17:23:17.443Z", "id": "507f1f77bcf86cd799439011"}
            ```
        """
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


class JsonSerializer(SerializerProtocol):
    """JSON serializer implementation with datetime and MongoDB ObjectId support.

    This class provides JSON serializer implementation that uses standard json module
    with custom encoder for datetime objects and MongoDB ObjectId.

    Features:
    - Datetime serialization/deserialization
    - MongoDB ObjectId serialization
    - Consistent JSON encoding settings
    - Compact output with sorted keys
    - UTF-8 support
    - Error handling
    """

    def __init__(self) -> None:
        """Initialize JSON serializer."""
        self._encoder = MongoJsonEncoder

    def _validate_cache_data(self, data: Any) -> bool:
        """Validate cache data structure.

        This method validates both basic data format and content.
        It ensures that:
        1. Data has valid type
        2. Dictionaries have at least one non-None value
        3. Lists contain valid items
        4. No invalid structures

        Args:
            data: Data to validate

        Returns:
            bool: True if data is valid, False otherwise

        Examples:
            >>> serializer = JsonSerializer()
            >>> serializer._validate_cache_data({"name": "test", "age": None})
            True
            >>> serializer._validate_cache_data(None)
            False
            >>> serializer._validate_cache_data([{"name": "test"}, {"name": None}])
            True
        """
        if data is None:
            logger.warning("Cache data is None")
            return False

        if isinstance(data, (str, int, float, bool)):
            return True

        if isinstance(data, list):
            # Empty list is valid
            if not data:
                return True

            # Validate each item in list
            valid_items = 0
            for item in data:  # type: ignore
                if isinstance(item, dict):
                    if any(v is not None for v in item.values()):  # type: ignore
                        valid_items += 1
                elif item is not None:
                    valid_items += 1

            # At least one valid item required if list is not empty
            if valid_items == 0 and data:
                logger.warning("No valid items in non-empty list")
                return False

            return True

        if isinstance(data, dict):
            if not data:
                logger.warning("Empty dict provided")
                return False

            # Check if dict has at least one non-None value
            if not any(v is not None for v in data.values()):  # type: ignore
                logger.warning("All values in dict are None")
                return False

            return True

        logger.warning(f"Invalid cache data type: {type(data)}")
        return False

    def dumps(self, value: Any) -> str:
        """Serialize value to JSON string.

        Args:
            value: Value to serialize

        Returns:
            str: Serialized value

        Raises:
            SerializationError: If serialization fails
        """
        try:
            if value is None:
                logger.warning("Attempting to serialize None value")
                return ""

            # Log original value for debugging
            logger.debug(f"Serializing value: {value}")

            # Validate value before serialization
            if not self._validate_cache_data(value):
                raise SerializationError(
                    f"Invalid data structure: {value}", backend="json"
                )

            # Convert to JSON with custom encoder
            start_time = time.time()
            result = json.dumps(
                value,
                cls=self._encoder,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            duration = (time.time() - start_time) * 1000

            if not result:
                raise SerializationError(
                    "Serialization produced empty result", backend="json"
                )

            # Log serialized result for debugging
            logger.debug(
                f"Serialized to {len(result)} bytes in {duration:.2f}ms: {result[:200]}..."
            )
            return result

        except Exception as e:
            logger.error(f"Failed to serialize value: {str(e)}", exc_info=True)
            raise SerializationError(
                f"Failed to serialize value: {str(e)}", backend="json"
            ) from e

    def loads(self, value: Optional[str]) -> Optional[JsonValue]:
        """Deserialize JSON string to Python object.

        Args:
            value: JSON string to deserialize

        Returns:
            Optional[JsonValue]: Deserialized object or None if deserialization failed
        """
        if not value:
            logger.warning("Empty value provided for deserialization")
            return None

        try:
            start_time = time.time()

            # First try to parse JSON
            result = json.loads(value)

            # Convert datetime strings
            if isinstance(result, dict):
                result = self._convert_datetime_strings(result)
                # Validate after conversion
                if not self._validate_cache_data(result):
                    logger.warning(
                        f"Invalid cache data format after conversion: {result}"
                    )
                    return None

            elif isinstance(result, list):
                result = [  # type: ignore
                    (
                        self._convert_datetime_strings(item)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in result  # type: ignore
                ]  # type: ignore
                # Validate list items
                if not self._validate_cache_data(result):
                    logger.warning(
                        f"Invalid cache data format in list after conversion: {result}"
                    )
                    return None

            duration = (time.time() - start_time) * 1000
            logger.debug(
                f"Deserialized to {type(result)} in {duration:.2f}ms: {str(result)[:200]}..."  # type: ignore
            )
            return result  # type: ignore

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize JSON: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"Failed to convert datetime strings: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during deserialization: {str(e)}")
            return None

    def _convert_datetime_strings(
        self, data: Any
    ) -> Union[JsonDict, JsonList, JsonPrimitive]:
        """Convert ISO format datetime strings back to datetime objects.

        This method recursively traverses the data structure and converts
        any ISO format datetime strings to datetime objects.

        Args:
            data: Data structure to convert

        Returns:
            Union[JsonDict, JsonList, JsonPrimitive]: Data structure with datetime strings converted to objects
        """
        if isinstance(data, str):
            try:
                return datetime.fromisoformat(data)  # type: ignore
            except ValueError:
                return data
        elif isinstance(data, dict):
            return {
                str(key): self._convert_datetime_strings(value)  # type: ignore
                for key, value in data.items()  # type: ignore
            }
        elif isinstance(data, list):
            return [self._convert_datetime_strings(item) for item in data]  # type: ignore
        return data
