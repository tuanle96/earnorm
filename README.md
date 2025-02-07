# EarnORM

[![Project Status: Prototype](https://img.shields.io/badge/Project%20Status-Prototype-yellow.svg)]()
[![License: CC BY-NC](https://img.shields.io/badge/License-CC%20BY--NC-lightgrey.svg)]()
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![PyPI version](https://badge.fury.io/py/earnorm.svg)](https://badge.fury.io/py/earnorm)

EarnORM is a high-performance, async-first MongoDB ORM for Python, designed to maximize throughput in I/O-bound applications. Built on top of Motor and Pydantic, it leverages the full power of async/await to handle thousands of database operations concurrently while maintaining type safety and data validation.

## 🌟 Key Highlights

- **Async-First Architecture**: Built from ground up with async/await for maximum I/O performance
- **Type Safety & Validation**: Full type hints and runtime validation powered by Pydantic
- **Powerful Query System**: Flexible domain expressions and advanced filtering capabilities
- **Relationship Management**: Comprehensive support for one-to-one, one-to-many, and many-to-many relationships
- **Developer Experience**: Rich set of tools, clear documentation, and extensive examples

## 🚀 Features

### Core Features
- **Model System**
  - Type-safe model definitions with Pydantic integration
  - Automatic schema validation and type conversion
  - Flexible field types with custom validation
  - Built-in support for indexes and constraints

- **Query System**
  - Powerful domain expressions for complex queries
  - Fluent interface for query building
  - Advanced filtering and sorting capabilities
  - Efficient batch operations support

- **Relationship Management**
  - One-to-one, one-to-many, many-to-many relationships
  - Lazy and eager loading strategies
  - Cascade operations support
  - Bidirectional relationship handling

### Performance Features
- **Connection Management**
  - Smart connection pooling with Motor
  - Automatic connection health monitoring
  - Pool metrics and diagnostics
  - Connection lifecycle management

- **Query Optimization**
  - Automatic index management
  - Query plan optimization
  - Efficient batch operations
  - Memory usage optimization

### Developer Tools
- **Documentation**
  - Comprehensive API documentation
  - Best practices guides
  - Code examples and tutorials
  - Integration examples with popular frameworks

- **Development Support**
  - Full IDE support with type hints
  - Clear error messages and validation
  - Debugging and logging utilities
  - Testing utilities and fixtures

**Notes:**
1. **Async Support**: EarnORM is built with async-first approach, while MongoEngine is sync-only
2. **Type Safety**: EarnORM and Beanie provide full type hints and runtime type checking
3. **GridFS**: EarnORM offers comprehensive GridFS support with streaming and metadata management
4. **Relationships**: EarnORM provides full relationship support with lazy loading and cascade operations
5. **Enterprise Features**: EarnORM includes advanced features like caching, events, and schema evolution
6. **Developer Experience**: All ODMs provide good documentation, but IDE support varies

Choose EarnORM if you need:
- Async-first development
- Strong type safety
- Advanced relationship features
- Enterprise-grade features
- Comprehensive GridFS support
- Modern Python development experience

## 🏗 Project Status

### ✅ Implemented
- **Core Features**
  - Async model system with Motor integration
  - Field types and validation
  - Basic relationship support
  - Domain expressions for querying
  - Collection and index management

- **Performance Features**
  - Connection pooling
  - Basic query optimization
  - Batch operations
  - Memory management

### 🚧 In Development
- **Core Features**
  - Advanced relationship features
  - Complex query optimization
  - Schema migration tools
  - Event system enhancements

- **Developer Tools**
  - CLI tools for common tasks
  - Additional testing utilities
  - Documentation improvements
  - More framework integration examples

## 📝 Documentation

### Getting Started
- [Installation Guide](https://earnorm.readthedocs.io/installation)
- [Quick Start Tutorial](https://earnorm.readthedocs.io/quickstart)
- [Basic Concepts](https://earnorm.readthedocs.io/concepts)

### Core Documentation
- [Model System](https://earnorm.readthedocs.io/models)
- [Query System](https://earnorm.readthedocs.io/queries)
- [Relationships](https://earnorm.readthedocs.io/relationships)
- [Field Types](https://earnorm.readthedocs.io/fields)

### Advanced Topics
- [Performance Optimization](https://earnorm.readthedocs.io/performance)
- [Connection Management](https://earnorm.readthedocs.io/connections)
- [Best Practices](https://earnorm.readthedocs.io/best-practices)

## 💡 Examples

### Basic Usage
```python
import asyncio
from earnorm import init, Model, fields

async def main():
    # Initialize EarnORM
    await init(
        mongo_uri="mongodb://localhost:27017",
        database="example"
    )

    class User(Model):
        _collection = "users"
        
        name = fields.String(required=True)
        email = fields.Email(required=True, unique=True)
        age = fields.Integer(required=True)

    # Create user
    user = await User.create({
        "name": "John",
        "email": "john@example.com",
        "age": 25
    })

    # Query users
    adult_users = await User.search([
        ("age", ">=", 18),
        ("status", "=", "active")
    ])

if __name__ == "__main__":
    asyncio.run(main())
```

### Relationship Example
```python
class User(Model):
    _collection = "users"
    
    name = fields.String(required=True)
    posts = relationships.OneToMany("Post", "author_id")

class Post(Model):
    _collection = "posts"
    
    title = fields.String(required=True)
    author = relationships.ManyToOne("User", "author_id")

# Query related records
user = await User.get(user_id)
user_posts = await user.posts.filter(status="published").all()
```

### Advanced Query Example
```python
from earnorm.domain import DomainBuilder

# Build complex query
domain = (
    DomainBuilder()
    .field("age").greater_than(18)
    .and_()
    .open_group()
        .field("role").in_(["admin", "manager"])
        .or_()
        .field("status").equals("active")
    .close_group()
    .build()
)

# Execute query
users = await User.search(domain)
```

[See more examples in our documentation](https://earnorm.readthedocs.io/examples)

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

EarnORM is released under the Creative Commons Attribution-NonCommercial (CC BY-NC) license.

## 📧 Contact

- Email: [contact@earnorm.dev](mailto:contact@earnorm.dev)
- GitHub Issues: [earnorm/issues](https://github.com/earnorm/earnorm/issues)

## ⭐️ Credits

EarnORM is developed by the EarnBase team and the open source community.

## Connection Pool Module

### Progress

#### Completed
- Protocol layer implementation (database, connection, operations)
- Error handling and custom exceptions
- MongoDB pool implementation with retry and circuit breaker
- Redis pool implementation with retry and circuit breaker
- Retry mechanism with exponential backoff
- Circuit breaker implementation
- Integration of retry and circuit breaker into pools
- Basic MySQL & PostgreSQL implementations with NotImplementedError
- Factory and Registry integration
- Cleanup of unused files (context.py)

#### In Progress
- Type hints fixes and improvements
- Documentation updates
- Testing setup

#### Pending (Future)
- Monitoring and metrics
- Redis pub/sub support
- Performance optimization
- Full MySQL & PostgreSQL implementations
- CI/CD pipeline setup

### Known Issues
1. Type hints:
   - Type variables `DB` and `COLL` need better definition
   - Method overrides have incompatible return types
   - MongoDB and Redis driver types need completion
   - Dictionary key type mismatch in pool implementations

2. Code Quality:
   - Unused imports in protocol files
   - Decorator type hints need improvement
   - Some methods lack proper error handling

### Next Steps
1. **Immediate Tasks**:
   - Fix type hints and linter errors
   - Complete documentation with new examples
   - Set up testing framework

2. **Future Tasks**:
   - Implement monitoring and metrics
   - Add Redis pub/sub support
   - Optimize performance
   - Implement full MySQL & PostgreSQL support
   - Set up CI/CD pipeline

### Usage Examples

```python
# Using Factory Pattern
from earnorm.pool.factory import PoolFactory

# Create MongoDB Pool
mongo_pool = PoolFactory.create(
    "mongodb",
    uri="mongodb://localhost:27017",
    database="test",
    min_size=1,
    max_size=10,
    retry_policy=RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=5.0,
    ),
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        reset_timeout=30.0,
        half_open_timeout=5.0,
    ),
)

# Create Redis Pool
redis_pool = PoolFactory.create(
    "redis",
    uri="redis://localhost:6379",
    min_size=1,
    max_size=10,
    retry_policy=RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=5.0,
    ),
    circuit_breaker=CircuitBreaker(
        failure_threshold=5,
        reset_timeout=30.0,
        half_open_timeout=5.0,
    ),
)

# Using Registry Pattern
from earnorm.pool.registry import PoolRegistry

# Register custom pool implementation
PoolRegistry.register("custom", CustomPool)

# Get pool class
pool_class = PoolRegistry.get("mongodb")
pool = pool_class(uri="mongodb://localhost:27017")
```
