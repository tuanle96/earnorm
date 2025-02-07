# Types Module

This module provides type definitions and protocols used throughout the EarnORM framework.

## Overview

The types module consists of several components:

1. Base Types (`base.py`)
   - JSON types and value types
   - Domain operators
   - Basic value types

2. Model Types (`models.py`)
   - Model protocol
   - Database model types
   - Model metadata types

3. Database Types (`database.py`)
   - Database protocol
   - Database operations
   - Connection management

4. Field Types (`fields.py`)
   - Field protocols
   - Field value types
   - Validation protocols
   - Comparison operators

## Directory Structure

```
types/
├── __init__.py         # Package exports
├── base.py            # Base type definitions
├── models.py          # Model type definitions
├── database.py        # Database type definitions
└── fields.py          # Field type definitions
```

## Key Features

### 1. Base Types
```python
from earnorm.types import JsonValue, JsonDict, DomainOperator, ValueType

# JSON types
json_value: JsonValue = {"key": "value", "list": [1, 2, 3]}
json_dict: JsonDict = {"name": "John", "age": 30}

# Domain operators
operator: DomainOperator = "="  # Valid operators: =, !=, >, >=, <, <=, etc.

# Basic value types
value: ValueType = "string"  # Can be str, int, float, bool, None
```

### 2. Model Types
```python
from earnorm.types import ModelProtocol, DatabaseModel

class User(ModelProtocol):
    """User model implementation.
    
    Examples:
        >>> user = await User.create({
        ...     "name": "John Doe",
        ...     "email": "john@example.com"
        ... })
        >>> print(user.name)  # John Doe
    """
    
    _store: bool = True
    _name: str = "user"
    _description: str = "User model"
    _table: str = "users"
    
    async def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email
        }
```

### 3. Database Types
```python
from earnorm.types import DatabaseProtocol

class MongoDatabase(DatabaseProtocol):
    """MongoDB database implementation.
    
    Examples:
        >>> db = MongoDatabase(uri="mongodb://localhost:27017")
        >>> await db.connect()
        >>> result = await db.fetch_one("users", {"id": "123"})
        >>> await db.disconnect()
    """
    
    async def connect(self) -> None:
        # Connect to database
        ...
        
    async def fetch_one(self, query: str, params: dict = None) -> dict:
        # Fetch single record
        ...
```

### 4. Field Types
```python
from earnorm.types import FieldProtocol, ValidatorProtocol

class StringField(FieldProtocol[str]):
    """String field implementation.
    
    Examples:
        >>> name = StringField(required=True, unique=True)
        >>> await name.validate("John")  # OK
        >>> await name.validate(123)  # Raises ValidationError
    """
    
    async def validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError("Value must be string")
            
    async def convert(self, value: Any) -> str:
        return str(value)
```

## Features

1. Type Safety
   - Runtime type checking
   - Protocol validation
   - Type hints
   - Generic types

2. Model Types
   - Model metadata
   - CRUD operations
   - Field definitions
   - Validation rules

3. Database Types
   - Connection management
   - Transaction support
   - Query execution
   - Error handling

4. Field Types
   - Value validation
   - Type conversion
   - Comparison operations
   - Relation handling

## Implementation Guide

### 1. Using Base Types

1. JSON types:
```python
from earnorm.types import JsonValue, JsonDict

def process_json(data: JsonValue) -> JsonDict:
    if isinstance(data, dict):
        return data
    return {"value": data}
```

2. Domain operators:
```python
from earnorm.types import DomainOperator

def build_query(field: str, op: DomainOperator, value: Any) -> dict:
    return {
        "field": field,
        "operator": op,
        "value": value
    }
```

### 2. Implementing Models

1. Basic model:
```python
from earnorm.types import ModelProtocol

class Product(ModelProtocol):
    _store = True
    _name = "product"
    _table = "products"
    
    async def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price
        }
```

2. Model operations:
```python
# Create record
product = await Product.create({
    "name": "Test Product",
    "price": 99.99
})

# Update record
await product.write({
    "price": 89.99
})

# Delete record
await product.unlink()
```

### 3. Database Integration

1. Database protocol:
```python
from earnorm.types import DatabaseProtocol

class Database(DatabaseProtocol):
    async def connect(self) -> None:
        # Connect to database
        ...
        
    async def execute(self, query: str, params: dict = None) -> Any:
        # Execute query
        ...
        
    async def begin(self) -> AsyncContextManager:
        # Begin transaction
        ...
```

2. Transaction handling:
```python
async with db.begin() as txn:
    # Execute queries
    await db.execute("INSERT INTO users (name) VALUES (:name)", 
                    {"name": "John"})
    # Commit on success, rollback on error
```

### 4. Field Implementation

1. Custom field:
```python
from earnorm.types import FieldProtocol, ValidatorProtocol

class EmailField(FieldProtocol[str]):
    name: str
    required: bool = True
    unique: bool = True
    validators: List[ValidatorProtocol] = []
    
    async def validate(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationError("Email must be string")
        if "@" not in value:
            raise ValidationError("Invalid email format")
```

2. Field validation:
```python
# Create validator
class EmailValidator(ValidatorProtocol):
    async def __call__(self, value: Any) -> bool:
        return isinstance(value, str) and "@" in value

# Use validator
email = EmailField(validators=[EmailValidator()])
await email.validate("test@example.com")  # OK
await email.validate("invalid")  # Raises ValidationError
```

## Best Practices

1. Type Safety
   - Use type hints
   - Implement protocols
   - Validate types
   - Handle errors

2. Model Design
   - Clear interfaces
   - Proper validation
   - Error handling
   - Documentation

3. Database Operations
   - Connection pooling
   - Transaction safety
   - Error handling
   - Resource cleanup

4. Field Implementation
   - Type conversion
   - Validation rules
   - Error messages
   - Documentation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
