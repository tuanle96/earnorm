# Base Package

This package provides the core functionality for EarnORM, including models, database access, and environment management.

## Overview

The base package consists of three main modules:

1. Model System (`model/`)
2. Database System (`database/`)
3. Environment System (`env/`)

## Directory Structure

```
base/
├── __init__.py      # Package exports
├── model/          # Model system
│   ├── __init__.py
│   ├── base.py    # Base model implementation
│   ├── meta.py    # Model metadata/metaclass
│   └── descriptors.py  # Field descriptors
├── database/      # Database system
│   ├── __init__.py
│   ├── adapter.py # Base adapter interface
│   ├── query/     # Query building system
│   └── transaction/ # Transaction management
├── env/          # Environment system
│   ├── __init__.py
│   └── base.py   # Environment implementation
└── README.md     # This file
```

## Modules

### 1. Model System (`model/`)

The model system provides the foundation for defining and working with database models:

```python
from earnorm.base.model import BaseModel
from earnorm.fields import StringField, IntegerField

class User(BaseModel):
    _name = 'data.user'
    
    name = StringField(required=True)
    age = IntegerField()
    
    async def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")

# Create record
user = await User.create({
    "name": "John Doe",
    "age": 30
})

# Search records
users = await User.search([
    ("age", ">=", 18)
])
```

Key features:
- Model definition
- Field validation
- CRUD operations
- Query building
- Event system

### 2. Database System (`database/`)

The database system handles database connections and operations:

```python
from earnorm.base.database import DatabaseAdapter
from earnorm.base.database.query import Query

# Create adapter
adapter = MongoAdapter(uri="mongodb://localhost:27017")

# Basic query
users = await adapter.query(User).filter(
    age__gt=18,
    status="active"
).all()

# Aggregate query
stats = await adapter.query(User, "aggregate")\
    .group_by("status")\
    .count("total")\
    .execute()

# Transaction
async with adapter.transaction() as txn:
    user = await txn.create(User, {
        "name": "John",
        "age": 30
    })
```

Key features:
- Database adapters
- Query building
- Transaction management
- Connection pooling
- Result mapping

### 3. Environment System (`env/`)

The environment system manages application state and dependencies:

```python
from earnorm.base.env import Environment
from earnorm.base.database import MongoAdapter

# Create environment
env = Environment()

# Register database
env.register_database(MongoAdapter(uri="mongodb://localhost:27017"))

# Get model with environment
User = env.get_model('data.user')

# Create record in environment
user = await User.with_env(env).create({
    "name": "John",
    "age": 30
})
```

Key features:
- Environment management
- Database registration
- Model registry
- Dependency injection
- Configuration management

## Features

### 1. Model Layer

- Model definition
- Field validation
- CRUD operations
- Query building
- Event system
- Field caching

### 2. Database Layer

- Multiple backends
- Query building
- Transaction support
- Connection pooling
- Result mapping
- Type conversion

### 3. Environment Layer

- Configuration
- Registry system
- Dependency injection
- Resource management
- Error handling

## Best Practices

### 1. Model Design

- Keep models focused
- Use inheritance wisely
- Document fields
- Add validation
- Handle errors

### 2. Database Usage

- Use transactions
- Handle connections
- Optimize queries
- Manage resources
- Monitor performance

### 3. Environment Management

- Configure properly
- Register dependencies
- Handle cleanup
- Monitor resources
- Log operations

## Implementation Guide

### 1. Setup Environment

```python
from earnorm.base.env import Environment
from earnorm.base.database import MongoAdapter

# Create environment
env = Environment()

# Configure database
db = MongoAdapter(
    uri="mongodb://localhost:27017",
    database="myapp"
)
env.register_database(db)

# Configure logging
env.configure_logging(level="INFO")
```

### 2. Define Models

```python
from earnorm.base.model import BaseModel
from earnorm.fields import StringField, IntegerField

class User(BaseModel):
    _name = 'data.user'
    _env = env  # Set environment
    
    name = StringField(required=True)
    age = IntegerField()
    
    async def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")
```

### 3. Use Database

```python
# Get database adapter
db = env.get_database()

# Basic query
users = await db.query(User).filter(
    age__gt=18
).all()

# Transaction
async with db.transaction() as txn:
    user = await User.with_env(txn).create({
        "name": "John",
        "age": 30
    })
```

### 4. Handle Events

```python
class Product(BaseModel):
    _name = 'data.product'
    _env = env
    
    async def before_create(self):
        if not self.code:
            self.code = generate_code()
            
    async def after_write(self):
        await self.update_index()
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
