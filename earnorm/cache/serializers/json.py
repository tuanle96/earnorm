"""JSON serializer implementation.

This module provides JSON serializer implementation that uses standard json module.

Examples:
    ```python
    from earnorm.cache.serializers.json import JsonSerializer

    # Create serializer
    serializer = JsonSerializer()

    # Serialize value
    value = {"name": "John", "age": 30}
    serialized = serializer.dumps(value)
    print(serialized)  # {"age":30,"name":"John"}

    # Deserialize value
    deserialized = serializer.loads(serialized)
    print(deserialized)  # {"name": "John", "age": 30}
    ```
"""

import json
from typing import Any

from earnorm.cache.core.serializer import SerializerProtocol


class JsonSerializer(SerializerProtocol):
    """JSON serializer implementation.

    This class provides JSON serializer implementation that uses standard json module.
    It ensures consistent JSON encoding settings across the application.

    Features:
    - Consistent JSON encoding settings
    - Compact output with sorted keys
    - UTF-8 support
    - Error handling

    Examples:
        ```python
        # Create serializer
        serializer = JsonSerializer()

        # Serialize dictionary
        value = {"name": "John", "age": 30}
        serialized = serializer.dumps(value)
        print(serialized)  # {"age":30,"name":"John"}

        # Serialize list
        value = [1, 2, 3]
        serialized = serializer.dumps(value)
        print(serialized)  # [1,2,3]

        # Deserialize value
        deserialized = serializer.loads(serialized)
        print(deserialized)  # [1, 2, 3]
        ```
    """

    def dumps(self, value: Any) -> str:
        """Serialize value to JSON string.

        Args:
            value: Value to serialize

        Returns:
            str: JSON string

        Raises:
            ValueError: If value cannot be serialized

        Examples:
            ```python
            # Serialize dictionary
            value = {"name": "John", "age": 30}
            serialized = serializer.dumps(value)
            print(serialized)  # {"age":30,"name":"John"}

            # Serialize list
            value = [1, 2, 3]
            serialized = serializer.dumps(value)
            print(serialized)  # [1,2,3]

            # Handle error
            try:
                serializer.dumps(object())
            except ValueError as e:
                print(e)  # Object of type 'object' is not JSON serializable
            ```
        """
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        except Exception as e:
            raise ValueError(f"Failed to serialize value: {e}") from e

    def loads(self, value: str) -> Any:
        """Deserialize JSON string to value.

        Args:
            value: JSON string

        Returns:
            Any: Deserialized value

        Raises:
            ValueError: If value cannot be deserialized

        Examples:
            ```python
            # Deserialize dictionary
            value = '{"age":30,"name":"John"}'
            deserialized = serializer.loads(value)
            print(deserialized)  # {"name": "John", "age": 30}

            # Deserialize list
            value = "[1,2,3]"
            deserialized = serializer.loads(value)
            print(deserialized)  # [1, 2, 3]

            # Handle error
            try:
                serializer.loads("invalid")
            except ValueError as e:
                print(e)  # Failed to deserialize value: Expecting value: line 1 column 1 (char 0)
            ```
        """
        try:
            return json.loads(value)
        except Exception as e:
            raise ValueError(f"Failed to deserialize value: {e}") from e
