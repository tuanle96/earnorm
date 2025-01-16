# Fields Module

## Overview
The Fields module provides field types and metadata for defining model fields in EarnORM.

## Components

### 1. Field Metadata (`metadata.py`)
- Field metadata storage
- Validation rules
- Index configuration
- Default values
- Custom options

```python
@dataclass
class FieldMetadata:
    name: str
    field_type: Type[Any]
    required: bool = False
    unique: bool = False
    index: bool = False
    default: Any = None
    description: Optional[str] = None
    validators: List[Callable[[Any], None]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
```

## Field Types

### 1. Basic Types
```python
class Char(Field):
    """String field."""
    def __init__(self, max_length: int = None, **kwargs):
        super().__init__(str, **kwargs)
        self.max_length = max_length

class Integer(Field):
    """Integer field."""
    def __init__(self, **kwargs):
        super().__init__(int, **kwargs)

class Float(Field):
    """Float field."""
    def __init__(self, **kwargs):
        super().__init__(float, **kwargs)

class Boolean(Field):
    """Boolean field."""
    def __init__(self, **kwargs):
        super().__init__(bool, **kwargs)
```

### 2. Complex Types
```python
class DateTime(Field):
    """DateTime field."""
    def __init__(self, auto_now: bool = False, **kwargs):
        super().__init__(datetime, **kwargs)
        self.auto_now = auto_now

class ObjectId(Field):
    """MongoDB ObjectId field."""
    def __init__(self, **kwargs):
        super().__init__(bson.ObjectId, **kwargs)

class List(Field):
    """List field."""
    def __init__(self, field_type: Type[Field], **kwargs):
        super().__init__(list, **kwargs)
        self.field_type = field_type
```

## Validation

### 1. Built-in Validators
```python
def max_length(length: int):
    def validator(value: str):
        if len(value) > length:
            raise ValueError(f"Value length must be <= {length}")
    return validator

def min_value(min_val: Union[int, float]):
    def validator(value: Union[int, float]):
        if value < min_val:
            raise ValueError(f"Value must be >= {min_val}")
    return validator
```

### 2. Custom Validators
```python
from earnorm.fields import Char, validator

class User(Model):
    email = Char(required=True)

    @validator("email")
    def validate_email(self, value: str):
        if "@" not in value:
            raise ValueError("Invalid email format")
```

## Indexing

### 1. Single Field Index
```python
class Product(Model):
    sku = Char(unique=True, index=True)
    name = Char(index=True)
```

### 2. TTL Index
```python
class Session(Model):
    created_at = DateTime(
        index=True,
        options={"expire_after_seconds": 3600}  # Expire after 1 hour
    )
```

## Best Practices

1. **Field Naming**
- Use snake_case
- Field names should clearly describe their purpose
- Avoid abbreviations

2. **Validation**
- Always validate required fields
- Add custom validators when needed
- Validate data types

3. **Indexing**
- Index frequently queried fields
- Use unique indexes for unique fields
- Consider performance implications when adding indexes

4. **Documentation**
- Add docstrings for custom fields
- Document validation rules
- Document index configuration

## Common Issues & Solutions

1. **Performance**
- Optimize indexes
- Use appropriate field types
- Avoid unnecessary validation

2. **Memory Usage**
- Limit field sizes
- Use appropriate data types
- Clean up expired documents

3. **Type Safety**
- Use type hints
- Validate data types
- Handle None values

## Contributing

1. Add docstrings for all fields
2. Implement unit tests
3. Follow type hints
4. Update documentation 
