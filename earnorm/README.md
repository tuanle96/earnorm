# EarnORM Framework

EarnORM is a powerful, async-first ORM (Object-Relational Mapping) framework for Python, designed to provide a flexible and type-safe interface for database operations.

## Core Features

1. **Async/Await Support**
   - Built from the ground up for async/await
   - Non-blocking database operations
   - Async connection pooling
   - Async event system

2. **Multiple Database Support**
   - MongoDB integration
   - PostgreSQL support
   - MySQL compatibility
   - Redis integration

3. **Type Safety**
   - Full type hints support
   - Runtime type checking
   - Validation system
   - Custom type converters

4. **Connection Pooling**
   - Efficient connection management
   - Automatic connection recovery
   - Circuit breaker pattern
   - Connection health checks

5. **Model System**
   - Declarative model definition
   - Field validation
   - Relationship management
   - Event hooks

## Module Structure

```
earnorm/
├── base/               # Core functionality
│   ├── model/         # Base model system
│   ├── database/      # Database abstraction
│   └── env/          # Environment management
│
├── fields/            # Field definitions
│   ├── primitive/    # Basic field types
│   ├── composite/    # Complex field types
│   ├── relation/     # Relationship fields
│   └── validators/   # Field validators
│
├── pool/              # Connection pooling
│   ├── core/         # Core pool functionality
│   └── backends/     # Database-specific pools
│
├── database/          # Database functionality
│   ├── adapters/     # Database adapters
│   └── query/        # Query building
│
├── di/                # Dependency injection
│   ├── container/    # DI container
│   └── lifecycle/    # Object lifecycle
│
├── config/            # Configuration management
│   └── model/        # Config models
│
└── types/            # Type definitions
```

## Quick Start

```python
from earnorm.base import BaseModel
from earnorm.fields import StringField, IntegerField
from earnorm.config import SystemConfig

# Define a model
class User(BaseModel):
    _name = 'data.user'
    name = StringField(required=True)
    age = IntegerField()

    async def validate(self):
        if self.age < 0:
            raise ValueError("Age cannot be negative")

# Initialize config
config = SystemConfig.load_env(".env")

# Create record
user = await User.create({
    "name": "John Doe",
    "age": 30
})

# Query records
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

## Key Components

### 1. Base Module
- Core functionality for models and database operations
- Environment management
- Base classes and interfaces

### 2. Fields Module
- Field type definitions
- Validation system
- Relationship management
- Custom field types

### 3. Pool Module
- Connection pooling
- Circuit breaker implementation
- Retry policies
- Health monitoring

### 4. Database Module
- Database adapters
- Query building
- Transaction management
- Type mapping

### 5. DI Module
- Dependency injection container
- Service lifecycle management
- Factory system
- Resource cleanup

### 6. Config Module
- Configuration management
- Environment variables
- YAML support
- Validation rules

## Best Practices

1. **Model Definition**
   - Use descriptive model names
   - Add field validation
   - Implement custom methods
   - Handle relationships properly

2. **Database Operations**
   - Use transactions for consistency
   - Implement proper error handling
   - Optimize queries
   - Monitor performance

3. **Connection Management**
   - Configure pool sizes appropriately
   - Implement health checks
   - Handle connection errors
   - Monitor pool metrics

4. **Type Safety**
   - Use type hints consistently
   - Validate input data
   - Handle type conversions
   - Test edge cases

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
