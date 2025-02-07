# Field Validators

This module provides field validation functionality for the EarnORM framework.

## Overview

The validators module includes validation classes for different field types:

1. Base Validator (`base.py`)
2. String Validators (`string.py`)
3. Number Validators (`number.py`)
4. DateTime Validators (`datetime.py`)

## Validator Types

### String Validators
```python
from earnorm.fields.validators import (
    LengthValidator,
    RegexValidator,
    EmailValidator,
    URLValidator
)

class User(BaseModel):
    # Length validation
    username = StringField(validators=[
        LengthValidator(min_length=3, max_length=50)
    ])
    
    # Pattern validation
    code = StringField(validators=[
        RegexValidator(pattern=r'^[A-Z]{2}\d{4}$')
    ])
    
    # Email validation
    email = StringField(validators=[EmailValidator()])
    
    # URL validation
    website = StringField(validators=[URLValidator()])
```

### Number Validators
```python
from earnorm.fields.validators import (
    RangeValidator,
    MultipleValidator,
    PrecisionValidator
)

class Product(BaseModel):
    # Range validation
    quantity = IntegerField(validators=[
        RangeValidator(min_value=0, max_value=1000)
    ])
    
    # Multiple validation
    size = IntegerField(validators=[
        MultipleValidator(base=5)
    ])
    
    # Precision validation
    price = DecimalField(validators=[
        PrecisionValidator(precision=2)
    ])
```

### DateTime Validators
```python
from earnorm.fields.validators import (
    DateRangeValidator,
    WeekdayValidator,
    TimeRangeValidator
)

class Event(BaseModel):
    # Date range validation
    date = DateField(validators=[
        DateRangeValidator(
            min_date="2024-01-01",
            max_date="2024-12-31"
        )
    ])
    
    # Weekday validation
    meeting_day = DateField(validators=[
        WeekdayValidator(allowed_days=[0, 1, 2, 3, 4])  # Mon-Fri
    ])
    
    # Time range validation
    start_time = TimeField(validators=[
        TimeRangeValidator(
            min_time="09:00:00",
            max_time="17:00:00"
        )
    ])
```

## Features

1. Base Validation
   - Type checking
   - Required fields
   - Default values
   - Custom messages
   - Error handling

2. String Validation
   - Length checks
   - Pattern matching
   - Format validation
   - Case sensitivity
   - Character sets

3. Number Validation
   - Range checking
   - Precision control
   - Multiple validation
   - Unit conversion
   - Format validation

4. DateTime Validation
   - Range checking
   - Format validation
   - Timezone handling
   - Weekday validation
   - Period validation

## Implementation Guide

### 1. Using Built-in Validators

1. Basic validation:
```python
# Single validator
name = StringField(validators=[
    LengthValidator(min_length=2, max_length=100)
])

# Multiple validators
age = IntegerField(validators=[
    RangeValidator(min_value=0, max_value=150),
    MultipleValidator(base=1)
])
```

2. Custom messages:
```python
# Custom error message
code = StringField(validators=[
    RegexValidator(
        pattern=r'^[A-Z]\d{5}$',
        message="Code must be 1 letter followed by 5 digits"
    )
])
```

### 2. Creating Custom Validators

1. Basic validator:
```python
from earnorm.fields.validators import BaseValidator

class EvenNumberValidator(BaseValidator):
    def validate(self, value: int) -> None:
        if value % 2 != 0:
            raise ValueError("Number must be even")
```

2. Parameterized validator:
```python
class MultipleOfValidator(BaseValidator):
    def __init__(self, base: int, message: Optional[str] = None):
        super().__init__(message)
        self.base = base
        
    def validate(self, value: int) -> None:
        if value % self.base != 0:
            raise ValueError(
                f"Number must be multiple of {self.base}"
            )
```

3. Async validator:
```python
class UniqueValidator(BaseValidator):
    async def validate(self, value: Any) -> None:
        exists = await self.model.search([
            (self.field_name, "=", value)
        ]).exists()
        
        if exists:
            raise ValueError(f"{value} already exists")
```

### 3. Combining Validators

1. Multiple validators:
```python
username = StringField(validators=[
    LengthValidator(min_length=3, max_length=50),
    RegexValidator(pattern=r'^[a-zA-Z0-9_]+$'),
    UniqueValidator()
])
```

2. Conditional validation:
```python
class ConditionalValidator(BaseValidator):
    def __init__(self, condition: Callable[[], bool], 
                 validator: BaseValidator):
        self.condition = condition
        self.validator = validator
        
    def validate(self, value: Any) -> None:
        if self.condition():
            self.validator.validate(value)
```

## Best Practices

1. Validation Design
   - Keep validators focused
   - Use clear messages
   - Handle edge cases
   - Consider performance
   - Document constraints

2. Error Handling
   - Use specific errors
   - Provide context
   - Handle nulls
   - Log failures
   - Return clear messages

3. Custom Validators
   - Inherit BaseValidator
   - Document behavior
   - Test thoroughly
   - Handle all cases
   - Follow conventions

4. Validation Chain
   - Order validators
   - Handle dependencies
   - Stop on first error
   - Combine efficiently
   - Document flow

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
