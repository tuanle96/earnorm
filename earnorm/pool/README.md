# Pool Module

## Overview

The Pool module provides connection pooling and resource management for database connections in EarnORM.

## Structure

```
pool/
├── core/          # Core pooling functionality
│   ├── pool.py    # Connection pool implementation
│   └── manager.py # Pool manager
├── backends/      # Database backend implementations
│   ├── mongo/     # MongoDB connection pool
│   └── redis/     # Redis connection pool
└── protocols/     # Pool protocols and interfaces
```

## Features

### 1. Connection Pool

```python
from earnorm.pool import Pool

# Create pool
pool = await Pool.create(
    uri="mongodb://localhost:27017",
    min_size=5,
    max_size=20
)

# Get connection
async with pool.acquire() as conn:
    await conn.find_one("users", {"id": "123"})
```

### 2. Pool Management

```python
from earnorm.pool import pool_manager

# Register pool
await pool_manager.register("default", pool)

# Get pool
pool = pool_manager.get("default")

# Close all pools
await pool_manager.close_all()
```

### 3. Connection Lifecycle

```python
from earnorm.pool import lifecycle

@lifecycle.on_connect
async def setup_connection(conn):
    await conn.set_read_concern("majority")

@lifecycle.on_release
async def cleanup_connection(conn):
    await conn.reset()
```

### 4. Pool Monitoring

```python
from earnorm.pool import metrics

# Get pool stats
stats = await pool.get_stats()
print(f"Active connections: {stats.active}")
print(f"Available connections: {stats.available}")

# Monitor pool events
@pool.on("overflow")
async def handle_overflow(pool):
    logger.warning(f"Pool {pool.name} is at capacity")
```

## Configuration

```python
from earnorm.pool import setup_pool

# MongoDB pool
await setup_pool(
    backend="mongodb",
    uri="mongodb://localhost:27017",
    min_size=5,
    max_size=20,
    max_idle_time=300,
    connect_timeout=30
)

# Redis pool
await setup_pool(
    backend="redis",
    host="localhost",
    port=6379,
    min_size=2,
    max_size=10
)
```

## Best Practices

1. **Pool Sizing**

- Set appropriate min/max sizes
- Monitor connection usage
- Consider application load
- Handle peak periods

2. **Connection Lifecycle**

- Implement connection validation
- Handle connection errors
- Clean up resources
- Monitor connection age

3. **Error Handling**

- Handle connection failures
- Implement retries
- Log connection errors
- Monitor error rates

4. **Performance**

- Use connection pooling
- Monitor pool metrics
- Optimize pool size
- Handle backpressure

## Common Issues & Solutions

1. **Connection Leaks**

- Use context managers
- Implement timeouts
- Monitor active connections
- Clean up stale connections

2. **Pool Exhaustion**

- Implement backpressure
- Monitor pool capacity
- Handle overflow gracefully
- Scale pool size

3. **Performance**

- Optimize connection reuse
- Monitor connection lifetime
- Handle connection errors
- Use appropriate pool size

## Contributing

1. Follow code style guidelines
2. Add comprehensive docstrings
3. Write unit tests
4. Update documentation
