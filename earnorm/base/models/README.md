# Models Module

## Overview

The Models module provides core components for defining and managing models in EarnORM.

## Components

### 1. Base Model (`base.py`)

- Base class for all models
- Provides CRUD operations
- Event handling
- Validation
- Serialization

```python
from earnorm.base.models import Model
from earnorm.fields import Char

class User(Model):
    name = Char()
    email = Char()

    @event_handler("user.registered")
    async def handle_register(self, event: Event):
        print(f"User {self.name} registered")
```

### 2. Decorators (`decorators.py`)

- Event handlers
- Field validators
- Model hooks

```python
@event_handler("user.created")
async def handle_user_created(self, event):
    # Handle user created event
    pass

@validator("email")
def validate_email(self, value):
    # Validate email
    pass
```

### 3. Validation (`validation.py`)

- Model validation
- Field validation
- Custom validators

### 4. Persistence (`persistence.py`)

- Model persistence
- MongoDB integration
- CRUD operations

### 5. Lifecycle (`lifecycle.py`)

- Model lifecycle hooks
- Before/After save
- Before/After delete

### 6. Types (`types.py`)

- Model type definitions
- Type hints
- Runtime type checking

### 7. Interfaces (`interfaces.py`)

- Model interfaces
- Protocol definitions

## Best Practices

1. **Model Definition**
```python
from earnorm.base.models import Model
from earnorm.fields import Char, Integer, Boolean

class Product(Model):
    name = Char(required=True)
    price = Integer(required=True)
    active = Boolean(default=True)

    @validator("price")
    def validate_price(self, value):
        if value < 0:
            raise ValueError("Price cannot be negative")
```

2. **Event Handling**
```python
@event_handler("product.created")
async def handle_product_created(self, event):
    # Send notification
    await notify_admin(f"New product {self.name} created")
```

3. **Custom Validation**
```python
async def validate(self):
    await super().validate()
    # Custom validation logic
    if self.end_date < self.start_date:
        raise ValueError("End date must be after start date")
```

## Common Issues & Solutions

1. **Circular Imports**
- Use lazy imports
- Import inside functions
- Use string references

2. **Performance**
- Use indexes
- Implement caching
- Optimize queries

3. **Type Safety**
- Use type hints
- Enable mypy checking
- Runtime type validation

## Contributing

1. Add docstrings for all public methods
2. Implement unit tests
3. Follow type hints
4. Update documentation 
