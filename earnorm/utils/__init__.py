"""Utilities for EarnORM.

This package provides various utility functions and classes used throughout
the EarnORM framework.

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

from earnorm.utils.json import dumps, loads

__all__ = ["dumps", "loads"]
