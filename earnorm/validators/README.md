# Validators Module

This module provides validation functionality for the EarnORM framework.

## Overview

The validators module consists of four main components:

1. Base Validators (`base.py`)
   - Base validator class
   - Validation exceptions
   - Validator creation helpers

2. Field Validators (`fields/`)
   - String validators (`string.py`)
   - Number validators (`number.py`) 
   - Composite validators (`composite.py`)

3. Model Validators (`models/`)
   - Reference validators (`reference.py`)
   - Unique validators (`unique.py`)
   - Custom validators (`custom.py`)

## Directory Structure

```
validators/
├── __init__.py         # Package exports
├── base.py            # Base validator implementation
├── fields/            # Field validators
│   ├── string.py     # String validation
│   ├── number.py     # Number validation
│   └── composite.py  # Composite validation
└── models/           # Model validators
    ├── reference.py  # Reference validation
    ├── unique.py     # Unique validation
    └── custom.py     # Custom validation
```

## Key Features

### 1. Base Validation
```python
from earnorm.validators import BaseValidator, ValidationError

class EmailValidator(BaseValidator):
    """Email validator implementation.
    
    Examples:
        >>> validator = EmailValidator()
        >>> validator("test@example.com")  # OK
        >>> validator("invalid")  # Raises ValidationError
    """
    
    def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError("Value must be string")
        if "@" not in value:
            raise ValidationError("Invalid email format")
```

### 2. Field Validation

1. String Validation:
```python
from earnorm.validators.fields.string import (
    EmailValidator, URLValidator, RegexValidator, validate_length
)

# Email validation
email = EmailValidator()
email("test@example.com")  # OK

# URL validation
url = URLValidator()
url("https://example.com")  # OK

# Regex validation
regex = RegexValidator(r"^[A-Z][a-z]+$")
regex("John")  # OK

# Length validation
validate_length("test", min_length=2, max_length=10)  # OK
```

2. Number Validation:
```python
from earnorm.validators.fields.number import (
    RangeValidator, validate_positive, validate_range
)

# Range validation
range_validator = RangeValidator(min_value=0, max_value=100)
range_validator(50)  # OK

# Positive validation
validate_positive(10)  # OK

# Range validation function
validate_range(5, min_value=0, max_value=10)  # OK
```

3. Composite Validation:
```python
from earnorm.validators.fields.composite import (
    ListItemValidator, DictSchemaValidator, validate_list_length
)

# List validation
list_validator = ListItemValidator(item_type=str)
list_validator(["a", "b", "c"])  # OK

# Dict validation
schema_validator = DictSchemaValidator({
    "name": str,
    "age": int
})
schema_validator({"name": "John", "age": 30})  # OK

# List length validation
validate_list_length([1, 2, 3], min_length=1, max_length=5)  # OK
```

### 3. Model Validation

1. Reference Validation:
```python
from earnorm.validators.models.reference import ExistsValidator

# Check if referenced record exists
exists = ExistsValidator("user")
await exists.validate("123")  # OK if user with ID 123 exists
```

2. Unique Validation:
```python
from earnorm.validators.models.unique import UniqueValidator

# Check if field value is unique
unique = UniqueValidator("email")
await unique.validate("test@example.com")  # OK if email is unique
```

3. Custom Validation:
```python
from earnorm.validators.models.custom import ModelValidator

class UserValidator(ModelValidator):
    async def validate(self, model: Any) -> None:
        if model.age < 18 and model.role == "admin":
            raise ValidationError("Admin must be 18 or older")
```

## Features

1. Field Validation
   - Type checking
   - Format validation
   - Range validation
   - Pattern matching
   - Custom validation

2. Model Validation
   - Reference integrity
   - Unique constraints
   - Custom rules
   - Async validation
   - Bulk validation

3. Validation Types
   - Sync validation
   - Async validation
   - Chain validation
   - Conditional validation
   - Custom validation

4. Error Handling
   - Detailed error messages
   - Custom error messages
   - Error aggregation
   - Error context
   - Error translation

## Implementation Guide

### 1. Creating Custom Validators

1. Basic validator:
```python
from earnorm.validators import BaseValidator, ValidationError

class PositiveValidator(BaseValidator):
    def __call__(self, value: Any) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationError("Value must be numeric")
        if value <= 0:
            raise ValidationError("Value must be positive")
```

2. Async validator:
```python
class UniqueEmailValidator(BaseValidator):
    async def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError("Value must be string")
        
        exists = await check_email_exists(value)
        if exists:
            raise ValidationError("Email already exists")
```

### 2. Using Validators

1. Field validation:
```python
from earnorm.fields import StringField
from earnorm.validators import EmailValidator

class User:
    email = StringField(
        validators=[EmailValidator()],
        required=True
    )
```

2. Model validation:
```python
from earnorm.validators.models import ModelValidator

class OrderValidator(ModelValidator):
    async def validate(self, order: Any) -> None:
        if order.total < 0:
            raise ValidationError("Total cannot be negative")
        if not order.items:
            raise ValidationError("Order must have items")
```

### 3. Validation Chains

1. Multiple validators:
```python
from earnorm.validators import (
    EmailValidator,
    UniqueValidator,
    validate_length
)

validators = [
    EmailValidator(),
    UniqueValidator("email"),
    lambda x: validate_length(x, max_length=100)
]

for validator in validators:
    await validator("test@example.com")
```

2. Conditional validation:
```python
class ConditionalValidator(BaseValidator):
    def __call__(self, value: Any) -> None:
        if isinstance(value, str):
            validate_length(value, max_length=100)
        elif isinstance(value, (int, float)):
            validate_range(value, min_value=0)
```

## Best Practices

1. Validator Design
   - Single responsibility
   - Clear error messages
   - Type safety
   - Performance

2. Error Handling
   - Descriptive messages
   - Context information
   - Error aggregation
   - Recovery options

3. Validation Flow
   - Type checking first
   - Format validation
   - Business rules
   - Custom logic

4. Performance
   - Efficient validation
   - Early returns
   - Caching results
   - Bulk validation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
