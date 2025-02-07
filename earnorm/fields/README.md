# Fields Module

This module provides field definitions and validation for the EarnORM framework. It includes primitive fields, composite fields, relations, and validators.

## Overview

The fields module consists of five main components:

1. Base Fields (`base.py`)
2. Primitive Fields (`primitive/`)
3. Composite Fields (`composite/`)
4. Relation Fields (`relation/`)
5. Validators (`validators/`)

## Directory Structure

```
fields/
├── __init__.py         # Package exports
├── base.py            # Base field implementation
├── interface.py       # Field interfaces
├── types.py          # Field type definitions
├── primitive/        # Primitive field types
│   ├── __init__.py
│   ├── string.py    # String fields
│   ├── number.py    # Numeric fields
│   ├── boolean.py   # Boolean fields
│   └── datetime.py  # Date/time fields
├── composite/       # Composite field types
│   ├── __init__.py
│   ├── array.py    # Array/list fields
│   ├── dict.py     # Dictionary fields
│   └── json.py     # JSON fields
├── relation/       # Relation field types
│   ├── __init__.py
│   ├── one2one.py  # One-to-one relations
│   ├── one2many.py # One-to-many relations
│   └── many2many.py# Many-to-many relations
└── validators/     # Field validators
    ├── __init__.py
    ├── base.py     # Base validator
    ├── string.py   # String validators
    ├── number.py   # Numeric validators
    └── datetime.py # Date/time validators
```

## Key Features

### 1. Primitive Fields
```python
from earnorm.fields import StringField, IntegerField, BooleanField, DateTimeField

class User(BaseModel):
    name = StringField(required=True, min_length=2, max_length=100)
    age = IntegerField(min_value=0, max_value=150)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

### 2. Composite Fields
```python
from earnorm.fields import ArrayField, DictField, JsonField

class Product(BaseModel):
    tags = ArrayField(StringField(), default=[])
    metadata = DictField(required=False)
    config = JsonField(default={})
```

### 3. Relation Fields
```python
from earnorm.fields import One2OneField, One2ManyField, Many2ManyField

class Order(BaseModel):
    user = One2OneField("User", required=True)
    items = One2ManyField("OrderItem")
    tags = Many2ManyField("Tag")
```

### 4. Field Validation
```python
from earnorm.fields.validators import (
    LengthValidator,
    RangeValidator,
    RegexValidator
)

class User(BaseModel):
    username = StringField(
        validators=[
            LengthValidator(min_length=3, max_length=50),
            RegexValidator(pattern=r'^[a-zA-Z0-9_]+$')
        ]
    )
    age = IntegerField(
        validators=[
            RangeValidator(min_value=0, max_value=150)
        ]
    )
```

## Features

1. Field Types
   - Primitive types (string, number, boolean, datetime)
   - Composite types (array, dict, json)
   - Relation types (one2one, one2many, many2many)
   - Custom field types

2. Field Validation
   - Type validation
   - Value constraints
   - Custom validators
   - Async validation
   - Error handling

3. Field Options
   - Required/optional
   - Default values
   - Read-only/write-only
   - Index support
   - Unique constraints

4. Field Conversion
   - Type conversion
   - Format handling
   - Serialization
   - Deserialization

## Implementation Guide

### 1. Using Fields

1. Define fields in models:
```python
from earnorm.fields import StringField, IntegerField
from earnorm.base import BaseModel

class User(BaseModel):
    name = StringField(required=True)
    age = IntegerField(default=0)
```

2. Field options:
```python
# Required field
name = StringField(required=True)

# Field with default
status = StringField(default="active")

# Read-only field
created_at = DateTimeField(readonly=True)

# Indexed field
email = StringField(index=True)
```

3. Field validation:
```python
# Built-in validation
age = IntegerField(min_value=0, max_value=150)

# Custom validation
def validate_email(value: str) -> None:
    if "@" not in value:
        raise ValueError("Invalid email format")

email = StringField(validators=[validate_email])
```

### 2. Using Relations

1. One-to-one relation:
```python
class User(BaseModel):
    profile = One2OneField("Profile")

class Profile(BaseModel):
    user = One2OneField("User")
```

2. One-to-many relation:
```python
class User(BaseModel):
    posts = One2ManyField("Post")

class Post(BaseModel):
    author = One2OneField("User")
```

3. Many-to-many relation:
```python
class Post(BaseModel):
    tags = Many2ManyField("Tag")

class Tag(BaseModel):
    posts = Many2ManyField("Post")
```

### 3. Custom Fields

1. Create custom field:
```python
from earnorm.fields import BaseField

class EmailField(BaseField[str]):
    def validate(self, value: str) -> None:
        super().validate(value)
        if "@" not in value:
            raise ValueError("Invalid email format")
```

2. Use custom field:
```python
class User(BaseModel):
    email = EmailField(required=True)
```

## Best Practices

1. Field Definition
   - Use descriptive field names
   - Set appropriate constraints
   - Add field documentation
   - Handle edge cases

2. Validation
   - Validate at field level
   - Add custom validators
   - Handle validation errors
   - Log validation failures

3. Relations
   - Define both sides
   - Set cascade options
   - Handle circular refs
   - Manage indexes

4. Custom Fields
   - Inherit from BaseField
   - Implement validation
   - Handle conversion
   - Add documentation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
