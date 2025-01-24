"""Serializer protocol definition.

This module provides protocol for cache value serializers.

Examples:
    ```python
    from typing import Any, Protocol

    from earnorm.cache.core.serializer import SerializerProtocol

    class MySerializer(SerializerProtocol):
        def dumps(self, value: Any) -> str:
            return str(value)

        def loads(self, value: str) -> Any:
            return eval(value)

    # Create serializer
    serializer = MySerializer()

    # Serialize value
    value = {"name": "John", "age": 30}
    serialized = serializer.dumps(value)
    print(serialized)  # {'name': 'John', 'age': 30}

    # Deserialize value
    deserialized = serializer.loads(serialized)
    print(deserialized)  # {"name": "John", "age": 30}
    ```
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SerializerProtocol(Protocol):
    """Protocol for cache value serializers.

    This protocol defines interface for cache value serializers.
    All serializers must implement this protocol.

    Features:
    - Runtime protocol checking
    - Type hints
    - Error handling

    Examples:
        ```python
        from typing import Any, Protocol

        class MySerializer(SerializerProtocol):
            def dumps(self, value: Any) -> str:
                return str(value)

            def loads(self, value: str) -> Any:
                return eval(value)

        # Create serializer
        serializer = MySerializer()

        # Serialize value
        value = {"name": "John", "age": 30}
        serialized = serializer.dumps(value)
        print(serialized)  # {'name': 'John', 'age': 30}

        # Deserialize value
        deserialized = serializer.loads(serialized)
        print(deserialized)  # {"name": "John", "age": 30}
        ```
    """

    def dumps(self, value: Any) -> str:
        """Serialize value to string.

        Args:
            value: Value to serialize

        Returns:
            str: Serialized value

        Raises:
            ValueError: If value cannot be serialized

        Examples:
            ```python
            # Serialize dictionary
            value = {"name": "John", "age": 30}
            serialized = serializer.dumps(value)
            print(serialized)  # {'name': 'John', 'age': 30}

            # Serialize list
            value = [1, 2, 3]
            serialized = serializer.dumps(value)
            print(serialized)  # [1, 2, 3]

            # Handle error
            try:
                serializer.dumps(object())
            except ValueError as e:
                print(e)  # Failed to serialize value
            ```
        """
        ...

    def loads(self, value: str) -> Any:
        """Deserialize value from string.

        Args:
            value: Serialized value

        Returns:
            Any: Deserialized value

        Raises:
            ValueError: If value cannot be deserialized

        Examples:
            ```python
            # Deserialize dictionary
            value = "{'name': 'John', 'age': 30}"
            deserialized = serializer.loads(value)
            print(deserialized)  # {"name": "John", "age": 30}

            # Deserialize list
            value = "[1, 2, 3]"
            deserialized = serializer.loads(value)
            print(deserialized)  # [1, 2, 3]

            # Handle error
            try:
                serializer.loads("invalid")
            except ValueError as e:
                print(e)  # Failed to deserialize value
            ```
        """
        ...
