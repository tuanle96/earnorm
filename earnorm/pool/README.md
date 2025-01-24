# Connection Pool Module

This module provides a flexible and robust connection pooling implementation for various database backends.

## Structure

- `protocols/`: Protocol definitions for database operations
  - `database.py`: Database protocol definitions
  - `connection.py`: Connection protocol definitions
  - `pool.py`: Pool protocol definitions
  - `errors.py`: Custom exceptions
  - `operations.py`: Operation type definitions

- `backends/`: Backend implementations
  - `mongo/`: MongoDB implementation
  - `redis/`: Redis implementation
  - `mysql/`: MySQL implementation (placeholder)
  - `postgres/`: PostgreSQL implementation (placeholder)

- `utils.py`: Utility functions for connection management
- `retry.py`: Retry mechanism with exponential backoff
- `circuit.py`: Circuit breaker implementation
- `decorators.py`: Decorators for retry and circuit breaker

## Progress

### Completed
- Protocol layer implementation
- Error handling and custom exceptions
- MongoDB and Redis pool implementations
- Retry mechanism and circuit breaker
- Connection utilities and helper functions

### In Progress
- Testing (unit tests and integration tests)
- Documentation (docstrings and examples)
- Type hints improvements

### Pending
- Monitoring and metrics
- Performance optimization
- Redis pub/sub support
- CI/CD pipeline setup

## Known Issues
- Type hints need improvement in some areas
- Some unused imports in protocol files (used in docstrings)
- Need to review error handling in backend implementations

## Next Steps
1. Complete test suite
2. Improve documentation
3. Add monitoring and metrics
4. Set up CI/CD pipeline

## Usage Examples

### MongoDB Pool
```python
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.retry import RetryPolicy
from earnorm.pool.circuit import CircuitBreaker

pool = MongoPool(
    uri="mongodb://localhost:27017",
    database="test",
    min_size=1,
    max_size=10,
    retry_policy=RetryPolicy(max_retries=3),
    circuit_breaker=CircuitBreaker(failure_threshold=5),
)

async with pool.connection() as conn:
    await conn.execute_typed("find_one", "users", filter={"name": "test"})
```

### Redis Pool
```python
from earnorm.pool.backends.redis import RedisPool
from earnorm.pool.retry import RetryPolicy
from earnorm.pool.circuit import CircuitBreaker

pool = RedisPool(
    uri="redis://localhost:6379",
    min_size=1,
    max_size=10,
    retry_policy=RetryPolicy(max_retries=3),
    circuit_breaker=CircuitBreaker(failure_threshold=5),
)

async with pool.connection() as conn:
    await conn.execute_typed("get", "key")
``` 
