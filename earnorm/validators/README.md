# Validators Module

## Overview
The Validators module provides a comprehensive validation system for EarnORM, supporting both synchronous and asynchronous validation for fields and models.

## Structure

```
validators/
├── base.py        # Base validator implementation
├── types.py       # Type definitions
├── fields/        # Field validators
│   ├── string.py  # String validation
│   ├── number.py  # Number validation
│   └── composite.py # Composite type validation
└── models/        # Model validators
    ├── custom.py  # Custom model validation
    ├── reference.py # Reference validation
    └── unique.py  # Uniqueness validation
```

## Components

### 1. Base Validation
Base classes and utilities for creating validators:
```python
from earnorm.validators import BaseValidator, ValidationError

class EmailValidator(BaseValidator):
    """Email address validator."""
    
    def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        if "@" not in value:
            raise ValidationError("Invalid email address")

# Quick validator creation
validate_positive = create_validator(
    lambda x: x > 0,
    "Value must be positive"
)
```

### 2. Field Validators
Built-in validators for different field types:

#### String Validators
```python
from earnorm.validators import (
    EmailValidator, 
    URLValidator,
    RegexValidator,
    validate_length
)

# Email validation
email = EmailValidator()
email("user@example.com")  # OK
email("invalid")  # Raises ValidationError

# URL validation
url = URLValidator()
url("https://example.com")  # OK

# Regex validation
pattern = RegexValidator(r"^[A-Z][a-z]+$")
pattern("Hello")  # OK

# Length validation
length = validate_length(min_length=3, max_length=10)
length("test")  # OK
```

#### Number Validators
```python
from earnorm.validators import (
    RangeValidator,
    validate_positive,
    validate_range
)

# Range validation
range_check = RangeValidator(min_value=0, max_value=100)
range_check(50)  # OK

# Positive number
validate_positive(10)  # OK
validate_positive(-1)  # Raises ValidationError

# Custom range
validate_range(0, 100)(50)  # OK
```

#### Composite Validators
```python
from earnorm.validators import (
    validate_list_items,
    validate_dict_schema,
    validate_list_length
)

# List validation
validate_list_items(validate_positive)([1, 2, 3])  # OK
validate_list_length(min_length=1)([1, 2, 3])  # OK

# Dict validation
schema = {
    "name": validate_length(max_length=50),
    "age": validate_positive
}
validate_dict_schema(schema)({"name": "John", "age": 30})  # OK
```

### 3. Model Validators
Validators for model-level validation:

```python
from earnorm.validators import (
    ModelValidator,
    AsyncModelValidator,
    validate_unique,
    validate_exists
)

class User(Model):
    name = fields.Char()
    email = fields.Char()
    
    # Unique field validation
    @validate_unique("email")
    async def validate_unique_email(self):
        pass
    
    # Reference validation
    @validate_exists("department_id", model="Department")
    async def validate_department(self):
        pass
    
    # Custom validation
    @ModelValidator
    def validate_age(self):
        if self.age < 0:
            raise ValidationError("Age cannot be negative")
```

## Configuration

### 1. Field Level
```python
class User(Model):
    name = fields.Char(
        validators=[
            validate_length(max_length=50),
            RegexValidator(r"^[A-Za-z ]+$")
        ]
    )
    age = fields.Integer(
        validators=[
            validate_range(0, 150)
        ]
    )
```

### 2. Model Level
```python
class Order(Model):
    @ModelValidator
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date must be after start date")
            
    @AsyncModelValidator
    async def validate_customer(self):
        customer = await Customer.get_by_id(self.customer_id)
        if not customer:
            raise ValidationError("Customer does not exist")
```

## Best Practices

1. **Validator Design**
- Keep validators focused and single-purpose
- Use descriptive error messages
- Handle edge cases
- Consider performance impact

2. **Field Validation**
- Use appropriate validators for field types
- Combine validators when needed
- Validate at the right level
- Handle null values properly

3. **Model Validation**
- Use model validators for cross-field validation
- Implement async validation when needed
- Consider validation order
- Handle complex business rules

4. **Error Handling**
- Provide clear error messages
- Handle validation errors gracefully
- Log validation failures
- Return meaningful errors

## Common Issues & Solutions

1. **Performance**
- Cache validation results when possible
- Use async validation efficiently
- Optimize complex validations
- Batch validations when possible

2. **Complexity**
- Break down complex validations
- Use composition
- Implement reusable validators
- Document validation rules

3. **Error Handling**
- Implement proper error handling
- Provide clear error messages
- Handle edge cases
- Log validation failures

## Contributing

1. Follow code style guidelines
2. Add comprehensive docstrings
3. Write unit tests
4. Update documentation 
