# EarnORM Pool Module

The pool module provides connection pooling functionality for various database backends.

## Features

- Multiple backend support (MongoDB, Redis, PostgreSQL)
- Connection lifecycle management
- Health checks and validation
- Metrics collection
- Configurable pool size and timeouts
- Connection reuse and cleanup

## Usage

### MongoDB Pool

```python
from earnorm.pool.backends.mongo.pool import MongoPool

# Create pool
pool = MongoPool(
    uri="mongodb://localhost:27017",
    database="test",
    min_size=5,
    max_size=20,
    timeout=30.0,
    max_lifetime=3600,
    idle_timeout=300,
    validate_on_borrow=True,
    test_on_return=True
)

# Initialize pool
await pool.init()

# Acquire connection
conn = await pool.acquire()

# Execute operations
result = await conn.execute("find_one", "users", {"name": "John"})
print(result)  # {"_id": "...", "name": "John", "age": 30}

# Release connection
await pool.release(conn)

# Close pool
await pool.close()
```

### Pool Manager

```python
from earnorm.pool.manager import PoolManager
from earnorm.pool.backends.mongo.pool import MongoPool

# Create manager
manager = PoolManager()

# Register pool types
manager.register_pool_type("mongodb", MongoPool)

# Create named pool
pool = await manager.create_pool(
    "mongodb",
    pool_name="users",
    uri="mongodb://localhost:27017",
    database="test"
)

# Get pool by name
pool = manager.get_pool("users")

# Close all pools
await manager.close_all()
```

## Best Practices

1. **Pool Lifecycle**
   - Always initialize pools before use with `await pool.init()`
   - Close pools when done with `await pool.close()`
   - Use context managers when possible

2. **Connection Management**
   - Always release connections after use
   - Don't keep connections for too long
   - Handle connection errors gracefully

3. **Configuration**
   - Set appropriate pool sizes based on workload
   - Configure timeouts based on operation types
   - Enable validation for critical operations

4. **Error Handling**
   - Handle connection errors
   - Handle pool exhaustion
   - Handle timeout errors

## API Reference

### Pool Protocol

```python
class PoolProtocol(Protocol[C]):
    @property
    def backend_type(self) -> str: ...
    
    @property
    def size(self) -> int: ...
    
    @property
    def available(self) -> int: ...
    
    async def init(self, **config: Dict[str, Any]) -> None: ...
    
    async def acquire(self) -> C: ...
    
    async def release(self, conn: C) -> None: ...
    
    async def close(self) -> None: ...
```

### Connection Protocol

```python
class ConnectionProtocol(Protocol):
    @property
    def created_at(self) -> float: ...
    
    @property
    def last_used_at(self) -> float: ...
    
    @property
    def idle_time(self) -> float: ...
    
    @property
    def lifetime(self) -> float: ...
    
    @property
    def is_stale(self) -> bool: ...
    
    def touch(self) -> None: ...
    
    async def ping(self) -> bool: ...
    
    async def close(self) -> None: ...
    
    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any: ...
```

### Pool Manager

```python
class PoolManager:
    def register_pool_type(self, backend_type: str, pool_type: Type[P]) -> None: ...
    
    async def create_pool(
        self,
        backend_type: str,
        pool_name: Optional[str] = None,
        **config: Any
    ) -> PoolProtocol[Any]: ...
    
    def get_pool(self, pool_name: str) -> Optional[PoolProtocol[Any]]: ...
    
    async def close_all(self) -> None: ...
```

## Contributing

1. Follow the project's coding style
2. Add tests for new features
3. Update documentation
4. Submit pull requests

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
