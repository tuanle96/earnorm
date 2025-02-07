# Database Adapters

This directory contains database-specific adapter implementations for EarnORM.

## Overview

Database adapters provide concrete implementations of the `DatabaseAdapter` interface for specific database backends. Each adapter handles:

1. Connection Management
2. Query Translation
3. Result Mapping
4. Transaction Management

## Available Adapters

### MongoDB Adapter

The MongoDB adapter (`mongo.py`) provides integration with MongoDB:

```python
from earnorm.base.database.adapters import MongoAdapter

# Create adapter
adapter = MongoAdapter(
    uri="mongodb://localhost:27017",
    database="mydb"
)

# Initialize
await adapter.init()

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

# Close when done
await adapter.close()
```

Features:
- Native MongoDB query support
- BSON type handling
- Index management
- Aggregation pipeline
- Change streams
- Transaction support (requires replica set)

## Implementing New Adapters

To add support for a new database, create a new adapter class that implements `DatabaseAdapter`:

```python
from earnorm.base.database import DatabaseAdapter
from earnorm.types import DatabaseModel

class PostgresAdapter(DatabaseAdapter[DatabaseModel]):
    async def init(self) -> None:
        # Initialize connection pool
        pass
        
    async def close(self) -> None:
        # Close connections
        pass
        
    async def query(self, model_type: Type[ModelT], query_type: str = "base"):
        # Implement query building
        pass
        
    async def get_connection(self) -> Any:
        # Get connection from pool
        pass
```

Requirements:
1. Must implement all abstract methods
2. Must handle connection lifecycle
3. Must support transactions
4. Must implement query building
5. Must handle type conversion

## Best Practices

1. Connection Management
- Use connection pooling
- Handle connection errors
- Implement retry logic
- Monitor connection health

2. Query Building
- Use parameterized queries
- Implement query optimization
- Handle complex joins
- Support aggregations

3. Transaction Support
- Implement ACID properties
- Support nested transactions
- Handle deadlocks
- Provide savepoints

4. Error Handling
- Use custom exceptions
- Provide detailed error messages
- Implement logging
- Handle edge cases

## Testing

Each adapter should have comprehensive tests:

1. Unit Tests
- Test each method independently
- Test error conditions
- Test edge cases
- Test type conversion

2. Integration Tests
- Test with real database
- Test transactions
- Test concurrent access
- Test performance

## Contributing

To contribute a new adapter:

1. Create adapter class
2. Implement required methods
3. Add comprehensive tests
4. Add documentation
5. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
