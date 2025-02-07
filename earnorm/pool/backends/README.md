# Pool Backends

This module provides database-specific connection pool implementations for the EarnORM framework.

## Overview

The backends module includes pool implementations for different databases:

1. Base Pool (`base.py`)
   - Abstract base class
   - Common functionality
   - Interface definition

2. MongoDB Pool (`mongo.py`)
   - MongoDB connection pool
   - MongoDB-specific features
   - MongoDB health checks

3. Redis Pool (`redis.py`)
   - Redis connection pool
   - Redis-specific features
   - Redis health checks

## Features

### 1. Base Pool
```python
from earnorm.pool.backends import BasePool

class CustomPool(BasePool):
    """Custom pool implementation.
    
    Examples:
        >>> pool = CustomPool(
        ...     uri="custom://localhost:1234",
        ...     min_size=5,
        ...     max_size=20
        ... )
        >>> async with pool.acquire() as conn:
        ...     # Use connection
        ...     pass
    """
    
    async def _create_connection(self) -> Any:
        # Create connection
        ...
        
    async def _destroy_connection(self, conn: Any) -> None:
        # Destroy connection
        ...
        
    async def _validate_connection(self, conn: Any) -> bool:
        # Validate connection
        ...
```

### 2. MongoDB Pool
```python
from earnorm.pool.backends import MongoPool

# Create MongoDB pool
pool = MongoPool(
    uri="mongodb://localhost:27017",
    database="test",
    min_size=5,
    max_size=20,
    options={
        "ssl": True,
        "auth_source": "admin"
    }
)

# Use MongoDB pool
async with pool.acquire() as conn:
    db = conn[database]
    collection = db[collection]
    await collection.find_one({"_id": 1})
```

### 3. Redis Pool
```python
from earnorm.pool.backends import RedisPool

# Create Redis pool
pool = RedisPool(
    uri="redis://localhost:6379",
    min_size=5,
    max_size=20,
    options={
        "encoding": "utf-8",
        "decode_responses": True
    }
)

# Use Redis pool
async with pool.acquire() as conn:
    await conn.set("key", "value")
    value = await conn.get("key")
```

## Implementation Guide

### 1. Base Pool Features

1. Connection lifecycle:
```python
# Initialize pool
await pool.init()

# Acquire connection
async with pool.acquire() as conn:
    # Use connection
    ...

# Close pool
await pool.close()
```

2. Health checks:
```python
# Check pool health
health = await pool.check_health()

# Get pool metrics
metrics = await pool.get_metrics()

# Cleanup stale connections
await pool.cleanup()
```

### 2. MongoDB Features

1. Connection options:
```python
pool = MongoPool(
    uri="mongodb://localhost:27017",
    database="test",
    options={
        "ssl": True,
        "auth_source": "admin",
        "replica_set": "rs0",
        "read_preference": "secondary"
    }
)
```

2. MongoDB operations:
```python
async with pool.acquire() as conn:
    db = conn[database]
    
    # CRUD operations
    await db.users.insert_one({"name": "John"})
    await db.users.find_one({"name": "John"})
    await db.users.update_one(
        {"name": "John"},
        {"$set": {"age": 30}}
    )
    await db.users.delete_one({"name": "John"})
```

### 3. Redis Features

1. Connection options:
```python
pool = RedisPool(
    uri="redis://localhost:6379",
    options={
        "encoding": "utf-8",
        "decode_responses": True,
        "ssl": True,
        "ssl_cert_reqs": "required"
    }
)
```

2. Redis operations:
```python
async with pool.acquire() as conn:
    # String operations
    await conn.set("key", "value")
    await conn.get("key")
    
    # Hash operations
    await conn.hset("hash", "field", "value")
    await conn.hget("hash", "field")
    
    # List operations
    await conn.lpush("list", "value")
    await conn.rpop("list")
```

## Best Practices

1. Connection Management
   - Use context managers
   - Handle connection errors
   - Validate connections
   - Monitor pool health
   - Clean up resources

2. Pool Configuration
   - Set appropriate sizes
   - Configure timeouts
   - Enable validation
   - Handle cleanup
   - Monitor metrics

3. Error Handling
   - Handle connection errors
   - Implement retries
   - Use circuit breaker
   - Log failures
   - Monitor health

4. Performance
   - Optimize pool size
   - Monitor metrics
   - Handle cleanup
   - Use connection limits
   - Implement timeouts

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
