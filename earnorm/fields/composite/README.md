# Composite Fields

This module provides composite field types for the EarnORM framework.

## Overview

The composite fields module includes complex data type fields:

1. Array Fields (`array.py`)
2. Dictionary Fields (`dict.py`) 
3. JSON Fields (`json.py`)

## Field Types

### Array Fields
```python
from earnorm.fields.composite import ArrayField
from earnorm.fields.primitive import StringField, IntegerField

class Product(BaseModel):
    # Array of strings
    tags = ArrayField(StringField())
    
    # Array of integers
    scores = ArrayField(IntegerField(), default=[])
    
    # Nested arrays
    matrix = ArrayField(ArrayField(IntegerField()))
```

### Dictionary Fields
```python
from earnorm.fields.composite import DictField
from earnorm.fields.primitive import StringField

class User(BaseModel):
    # Simple dictionary
    metadata = DictField()
    
    # Typed dictionary
    settings = DictField(
        key_field=StringField(),
        value_field=StringField()
    )
```

### JSON Fields
```python
from earnorm.fields.composite import JsonField

class Config(BaseModel):
    # JSON data
    data = JsonField(default={})
    
    # Schema validation
    schema = JsonField(schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        }
    })
```

## Features

1. Array Fields
   - Type validation
   - Length constraints
   - Nested arrays
   - Default values
   - Item validation

2. Dictionary Fields
   - Key/value types
   - Schema validation
   - Nested dictionaries
   - Default values
   - Key validation

3. JSON Fields
   - Schema validation
   - Format validation
   - Compression
   - Indexing
   - Query support

## Implementation Guide

### 1. Array Fields

1. Basic usage:
```python
# Simple array
tags = ArrayField(StringField())

# With defaults
scores = ArrayField(IntegerField(), default=[])

# Fixed length
coordinates = ArrayField(FloatField(), length=3)
```

2. Validation options:
```python
# Length constraints
items = ArrayField(
    StringField(),
    min_length=1,
    max_length=10
)

# Item validation
numbers = ArrayField(
    IntegerField(min_value=0)
)

# Custom validation
def validate_unique(value: List[str]) -> None:
    if len(set(value)) != len(value):
        raise ValueError("Array must contain unique values")

tags = ArrayField(
    StringField(),
    validators=[validate_unique]
)
```

### 2. Dictionary Fields

1. Basic usage:
```python
# Simple dictionary
metadata = DictField()

# Typed dictionary
settings = DictField(
    key_field=StringField(),
    value_field=IntegerField()
)
```

2. Validation options:
```python
# Required keys
config = DictField(
    required_keys=["host", "port"]
)

# Key pattern
headers = DictField(
    key_pattern=r'^[A-Z][A-Z-]*$'
)

# Value validation
scores = DictField(
    value_field=IntegerField(min_value=0)
)
```

### 3. JSON Fields

1. Basic usage:
```python
# Simple JSON
data = JsonField()

# With default
config = JsonField(default={})
```

2. Schema validation:
```python
# JSON Schema
user_data = JsonField(
    schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name", "email"]
    }
)
```

3. Advanced options:
```python
# Compression
large_data = JsonField(compress=True)

# Custom encoder/decoder
custom_json = JsonField(
    encoder=CustomEncoder,
    decoder=CustomDecoder
)
```

## Best Practices

1. Array Fields
   - Set length constraints
   - Validate item types
   - Handle empty arrays
   - Consider performance
   - Use appropriate defaults

2. Dictionary Fields
   - Define key/value types
   - Validate required keys
   - Handle nested data
   - Consider serialization
   - Document structure

3. JSON Fields
   - Use schema validation
   - Handle large data
   - Consider indexing
   - Optimize queries
   - Validate format

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
