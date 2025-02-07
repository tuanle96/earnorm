# Model Module

This module provides the core model functionality for EarnORM.

## Overview

The model module consists of four main components:

1. Base Model System
2. Field Descriptors 
3. Model Metadata
4. Model Registry

### Base Model (`base.py`)

The base model system provides the foundation for all database models:

```python
from earnorm.base.model import BaseModel
from earnorm.fields import StringField, IntegerField

# Define model
class User(BaseModel):
    _name = 'data.user'  # Collection/table name
    
    name = StringField(required=True)
    age = IntegerField()
    
    async def validate(self):
        '''Custom validation logic'''
        if self.age < 0:
            raise ValueError("Age cannot be negative")

# Create record
user = await User.create({
    "name": "John Doe",
    "age": 30
})

# Search records
users = await User.search([
    ("age", ">=", 18),
    ("name", "like", "John%")
])

# Update records
await users.write({
    "age": 31
})

# Delete records 
await users.unlink()
```

### Field Descriptors (`descriptors.py`)

The descriptor system handles field access and caching:

```python
from earnorm.base.model.descriptors import AsyncFieldDescriptor
from earnorm.fields import StringField

# Field with async descriptor
name = AsyncFieldDescriptor(StringField())

# Async field access
value = await user.name  # Fetches from DB and caches
value = await user.name  # Returns from cache

# Cache invalidation
user._invalidate_cache('name')  # Force reload
```

### Model Metadata (`meta.py`)

The metadata system manages model registration and inheritance:

```python
from earnorm.base.model.meta import ModelMeta, ModelInfo

# Model metadata
info = ModelInfo(
    name='data.user',
    model_class=User,
    is_abstract=False,
    parent_models={'base.model'},
    fields={'name': StringField()}
)

# Model metaclass
class CustomModel(metaclass=ModelMeta):
    _name = 'custom.model'
    name = StringField()
```

## Directory Structure

```
model/
├── __init__.py      # Package exports
├── base.py         # Base model implementation
├── descriptors.py  # Field descriptors
├── meta.py        # Model metadata/metaclass
└── README.md      # This file
```

## Features

### 1. Model Definition

- Model inheritance
- Field declarations
- Model metadata
- Abstract models
- Model registration

### 2. Field Management

- Field validation
- Type conversion
- Default values
- Computed fields
- Field caching

### 3. CRUD Operations

- Create records
- Read/search records
- Update records
- Delete records
- Bulk operations

### 4. Query Building

- Domain expressions
- Field selection
- Sorting/ordering
- Pagination
- Joins/aggregations

### 5. Transaction Support

- ACID compliance
- Nested transactions
- Savepoints
- Error handling

### 6. Event System

- Pre/post hooks
- Validation events
- Change tracking
- Custom events

## Best Practices

### 1. Model Design

- Keep models focused
- Use inheritance wisely
- Document fields
- Add validation
- Handle errors

### 2. Field Usage

- Set field types
- Add constraints
- Use computed fields
- Cache efficiently
- Handle nulls

### 3. Query Building

- Use domain expressions
- Filter early
- Select needed fields
- Order results
- Handle pagination

### 4. Transaction Management

- Use context managers
- Handle errors
- Manage savepoints
- Monitor performance

## Implementation Guide

### 1. Define Model

```python
from earnorm.base.model import BaseModel
from earnorm.fields import StringField, IntegerField, DateTimeField

class User(BaseModel):
    """User model.
    
    This model represents a user in the system.
    It includes basic user information and validation.
    
    Examples:
        >>> user = await User.create({
        ...     "name": "John Doe",
        ...     "age": 30,
        ...     "email": "john@example.com"
        ... })
        >>> print(user.name)  # "John Doe"
    """
    
    _name = 'data.user'
    _description = 'User Model'
    
    name = StringField(required=True, help="User's full name")
    age = IntegerField(help="User's age in years")
    email = StringField(unique=True, help="User's email address")
    created_at = DateTimeField(readonly=True, help="Record creation time")
    
    async def validate(self):
        """Validate user data."""
        if self.age < 0:
            raise ValueError("Age cannot be negative")
        if not self.email:
            raise ValueError("Email is required")
```

### 2. Add Computed Fields

```python
from earnorm.fields import computed

class Order(BaseModel):
    _name = 'data.order'
    
    subtotal = FloatField()
    tax_rate = FloatField()
    
    @computed(depends=['subtotal', 'tax_rate'])
    def total(self):
        """Compute order total with tax."""
        return self.subtotal * (1 + self.tax_rate)
```

### 3. Use Transactions

```python
async with User.env.transaction() as txn:
    # Create user
    user = await User.with_env(txn).create({
        "name": "John Doe",
        "email": "john@example.com"
    })
    
    # Create order
    order = await Order.with_env(txn).create({
        "user_id": user.id,
        "amount": 100.00
    })
    
    # Transaction commits if no errors
```

### 4. Handle Events

```python
class Product(BaseModel):
    _name = 'data.product'
    
    async def before_create(self):
        """Pre-create hook."""
        if not self.code:
            self.code = generate_product_code()
            
    async def after_write(self):
        """Post-write hook."""
        await self.update_search_index()
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
