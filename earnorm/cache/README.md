# EarnORM Cache Module

The cache module provides Redis-based caching functionality for EarnORM. It includes connection management, automatic reconnection, and cache invalidation mechanisms.

## Features

- Optional Redis caching that can be enabled/disabled during initialization
- Automatic connection management with retry mechanism
- Cache invalidation on model updates
- Configurable TTL and key prefixes
- Health checking and automatic recovery
- Logging of cache operations and connection status

## Usage

### Basic Initialization

```python
from earnorm import init

# Initialize with caching enabled
await init(
    mongo_uri="mongodb://localhost:27017",
    database="earnbase",
    redis_uri="redis://localhost:6379/0"  # Optional - caching disabled if not provided
)
```

### Cache Configuration

The cache manager can be configured with several options:

```python
await init(
    mongo_uri="mongodb://localhost:27017", 
    database="earnbase",
    redis_uri="redis://localhost:6379/0",
    cache_config={
        "ttl": 3600,  # Default TTL in seconds
        "prefix": "earnorm:",  # Key prefix
        "max_retries": 3,  # Max reconnection attempts
        "retry_delay": 1.0,  # Initial delay between retries (exponential backoff)
        "health_check_interval": 30.0  # Seconds between health checks
    }
)
```

### Using Cache Decorators

```python
from earnorm import models, fields
from earnorm.cache.decorators import cached

class User(models.BaseModel):
    name = fields.String(required=True)
    email = fields.Email(required=True)
    
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_profile(self):
        return {
            "name": self.name,
            "email": self.email
        }
```

## Architecture

The cache module consists of several components:

1. **CacheManager**: Core class managing Redis connections and cache operations
2. **Cache Decorators**: Decorators for caching method results
3. **Model Integration**: Automatic cache invalidation on model updates

## Best Practices

1. **Key Management**
   - Use descriptive key prefixes
   - Include version numbers in keys if data structure may change
   - Keep keys reasonably short

2. **TTL Strategy** 
   - Set appropriate TTLs based on data volatility
   - Use shorter TTLs for frequently changing data
   - Consider infinite TTL for static data

3. **Invalidation Strategy**
   - Invalidate related caches on model updates
   - Use pattern-based deletion for related keys
   - Consider pre-warming cache for critical data

4. **Error Handling**
   - Gracefully handle Redis connection failures
   - Log cache errors appropriately
   - Fall back to database queries when cache is unavailable

5. **Monitoring**
   - Monitor cache hit/miss rates
   - Track connection status and errors
   - Set up alerts for persistent connection issues

## Future Improvements

1. Support for additional cache backends
2. Cache warming strategies
3. Advanced invalidation patterns
4. Cache statistics and monitoring
5. Integration with other ORMs
6. Distributed cache support 
