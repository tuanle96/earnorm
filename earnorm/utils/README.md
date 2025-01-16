# Utils Module

## Overview
The Utils module provides common utility functions and helpers used throughout EarnORM. It includes JSON handling, type conversions, and other shared functionality.

## Structure

```
utils/
├── __init__.py   # Module initialization
└── json.py       # JSON utilities
```

## Components

### 1. JSON Utilities
Consistent JSON serialization and deserialization across the framework:

```python
from earnorm.utils.json import dumps, loads

# Serialization
data = {
    "name": "John",
    "age": 30,
    "scores": [95, 87, 92],
    "metadata": {
        "active": True,
        "joined": "2024-01-15"
    }
}
json_str = dumps(data)

# Deserialization
data = loads(json_str)
print(data["name"])  # John
```

#### Features
- Consistent encoding/decoding settings
- Unicode support (ensure_ascii=False)
- Compact output (minimal whitespace)
- Sorted keys for consistent output
- Support for bytes input
- Type hints and validation

#### Type Definitions
```python
JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, List["JsonValue"], Dict[str, "JsonValue"]]
```

### 2. Serialization Examples

#### Basic Types
```python
# Strings
dumps("Hello")  # "Hello"

# Numbers
dumps(42)       # "42"
dumps(3.14)     # "3.14"

# Booleans
dumps(True)     # "true"
dumps(False)    # "false"

# None
dumps(None)     # "null"
```

#### Complex Types
```python
# Lists
dumps([1, 2, 3])  # "[1,2,3]"

# Nested Structures
dumps({
    "users": [
        {"id": 1, "name": "John"},
        {"id": 2, "name": "Jane"}
    ]
})

# Unicode
dumps({
    "name": "José",
    "city": "São Paulo"
})
```

### 3. Deserialization Examples

#### Basic Usage
```python
# Parse JSON string
data = loads('{"name":"John","age":30}')
print(data["name"])  # John

# Parse bytes
data = loads(b'{"name":"John","age":30}')
print(data["age"])   # 30
```

#### Error Handling
```python
try:
    data = loads('invalid json')
except json.JSONDecodeError as e:
    print(f"Failed to parse JSON: {e}")
```

## Best Practices

1. **JSON Handling**
- Use framework utilities instead of direct json module
- Handle encoding errors gracefully
- Consider data size in memory
- Validate JSON structure

2. **Performance**
- Cache serialized results when appropriate
- Handle large JSON efficiently
- Use streaming for large datasets
- Monitor memory usage

3. **Error Handling**
- Handle JSON decode errors
- Validate data structure
- Handle Unicode properly
- Log serialization errors

4. **Type Safety**
- Use type hints
- Validate data types
- Handle null values
- Check structure depth

## Common Issues & Solutions

1. **Unicode Handling**
- Use ensure_ascii=False
- Handle encoding errors
- Validate Unicode strings
- Consider character sets

2. **Performance**
- Cache when possible
- Use appropriate encodings
- Handle large objects
- Monitor memory usage

3. **Compatibility**
- Version JSON schemas
- Handle legacy formats
- Document changes
- Migrate data carefully

## Contributing

1. Follow code style guidelines
2. Add comprehensive docstrings
3. Write unit tests
4. Update documentation 
