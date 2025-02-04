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
from datetime import datetime
from typing import Any, Dict, List, Union

from bson import ObjectId

from earnorm.cache.core.serializer import SerializerProtocol
from earnorm.exceptions import SerializationError


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

    def dumps(self, value: Any) -> str:
        """Serialize value to JSON string.

        Args:
            value: Value to serialize

        Returns:
            str: JSON string

        Raises:
            SerializationError: If value cannot be serialized

        Examples:
            ```python
            # Serialize dictionary with datetime and ObjectId
            value = {
                "name": "John",
                "created_at": datetime.now(),
                "id": ObjectId()
            }
            serialized = serializer.dumps(value)
            print(serialized)
            # {"created_at":"2024-02-04T17:23:17.443Z","id":"507f1f77bcf86cd799439011","name":"John"}
            ```
        """
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
                cls=MongoJsonEncoder,
            )
        except Exception as e:
            raise SerializationError(
                f"Failed to serialize value: {e}", backend="json", original_error=e
            )

    def loads(self, value: str) -> Any:
        """Deserialize JSON string to value.

        Args:
            value: JSON string

        Returns:
            Any: Deserialized value with datetime objects restored

        Raises:
            SerializationError: If value cannot be deserialized

        Examples:
            ```python
            # Deserialize JSON with datetime and ObjectId
            value = '{"created_at":"2024-02-04T17:23:17.443Z","id":"507f1f77bcf86cd799439011","name":"John"}'
            deserialized = serializer.loads(value)
            print(deserialized)
            # {
            #     "name": "John",
            #     "created_at": datetime.datetime(2024, 2, 4, 17, 23, 17, 443000),
            #     "id": "507f1f77bcf86cd799439011"
            # }
            ```
        """
        try:
            data = json.loads(value)
            return self._convert_datetime_strings(data)
        except Exception as e:
            raise SerializationError(
                f"Failed to deserialize value: {e}", backend="json", original_error=e
            )

    def _convert_datetime_strings(
        self, data: Any
    ) -> Union[Dict[str, Any], List[Any], Any]:
        """Convert ISO format datetime strings back to datetime objects.

        This method recursively traverses the data structure and converts
        any ISO format datetime strings to datetime objects.

        Args:
            data: Data structure to convert

        Returns:
            Union[Dict[str, Any], List[Any], Any]: Data structure with datetime strings converted to objects
        """
        if isinstance(data, str):
            try:
                return datetime.fromisoformat(data)
            except ValueError:
                return data
        elif isinstance(data, dict):
            return {str(k): self._convert_datetime_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_datetime_strings(i) for i in data]
        return data
