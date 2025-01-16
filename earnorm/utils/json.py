"""JSON utilities.

This module provides utilities for JSON serialization and deserialization.
It wraps the standard json module to provide consistent encoding/decoding
across the framework.

Examples:
    ```python
    from earnorm.utils.json import dumps, loads

    # Serialize to JSON
    data = {"name": "John", "age": 30}
    json_str = dumps(data)

    # Deserialize from JSON
    data = loads(json_str)
    print(data["name"])  # John
    ```
"""

import json
from typing import Any, Dict, List, Union

JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, List["JsonValue"], Dict[str, "JsonValue"]]


def dumps(obj: Any) -> str:
    """Serialize object to JSON string.

    This function wraps json.dumps() to provide consistent encoding
    across the framework. It uses the following settings:
    - ensure_ascii=False: Allow non-ASCII characters
    - separators=(",", ":"): Compact output
    - sort_keys=True: Consistent output

    Args:
        obj: Python object to serialize

    Returns:
        JSON string

    Examples:
        ```python
        from earnorm.utils.json import dumps

        # Serialize dict
        data = {"name": "John", "age": 30}
        json_str = dumps(data)
        print(json_str)  # {"age":30,"name":"John"}

        # Serialize list
        data = [1, 2, 3]
        json_str = dumps(data)
        print(json_str)  # [1,2,3]

        # Serialize with Unicode
        data = {"name": "José"}
        json_str = dumps(data)
        print(json_str)  # {"name":"José"}
        ```
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def loads(s: Union[str, bytes]) -> JsonValue:
    """Deserialize JSON string to Python object.

    This function wraps json.loads() to provide consistent decoding
    across the framework.

    Args:
        s: JSON string or bytes

    Returns:
        Python object

    Examples:
        ```python
        from earnorm.utils.json import loads

        # Deserialize dict
        json_str = '{"name":"John","age":30}'
        data = loads(json_str)
        print(data["name"])  # John

        # Deserialize list
        json_str = "[1,2,3]"
        data = loads(json_str)
        print(data[0])  # 1

        # Deserialize with Unicode
        json_str = '{"name":"José"}'
        data = loads(json_str)
        print(data["name"])  # José
        ```
    """
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return json.loads(s)
