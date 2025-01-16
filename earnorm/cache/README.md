# Cache Module

## Overview
The Cache module provides a flexible caching system for EarnORM, supporting multiple backends and caching strategies.

## Structure

```
cache/
├── backends/       # Cache backend implementations
├── core/          # Core caching functionality
├── decorators/    # Caching decorators
└── lifecycle/     # Cache lifecycle management
```

## Features

### 1. Cache Backends
- Redis backend (default)
- In-memory backend
- Custom backend support

### 2. Caching Strategies
- TTL-based caching
- Pattern-based invalidation
- Prefix-based grouping
- Cache tags

### 3. Decorators
```python
from earnorm.cache import cached

class UserService:
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_user(self, user_id: str) -> User:
        return await User.get_by_id(user_id)

    @cached(tags=["user_list"])
    async def list_users(self, filter: dict) -> List[User]:
        return await User.find(filter)
```

### 4. Cache Management
```python
from earnorm.cache import cache_manager

# Invalidate specific cache
await cache_manager.invalidate("user:123")

# Invalidate by pattern
await cache_manager.invalidate_pattern("user:*")

# Invalidate by tag
await cache_manager.invalidate_tags(["user_list"])
```

## Configuration

```python
from earnorm.cache import setup_cache

# Redis configuration
await setup_cache(
    backend="redis",
    host="localhost",
    port=6379,
    db=0,
    password=None
)

# In-memory configuration
await setup_cache(
    backend="memory",
    max_size=1000,  # Maximum number of items
    ttl=3600       # Default TTL in seconds
)
```

## Best Practices

1. **Cache Keys**
- Use consistent naming conventions
- Include version in keys
- Keep keys short but descriptive
- Use proper prefixes

2. **TTL Settings**
- Set appropriate TTL values
- Use infinite TTL sparingly
- Consider data volatility
- Implement cache warming

3. **Invalidation**
- Use targeted invalidation
- Implement cache tags
- Handle race conditions
- Monitor cache size

4. **Performance**
- Cache frequently accessed data
- Avoid caching large objects
- Use batch operations
- Monitor hit rates

## Common Issues & Solutions

1. **Cache Consistency**
- Implement versioning
- Use cache tags
- Handle race conditions
- Validate cached data

2. **Memory Usage**
- Set appropriate TTL
- Monitor cache size
- Use compression
- Implement eviction policies

3. **Performance**
- Use batch operations
- Optimize key design
- Monitor backend performance
- Handle cache misses efficiently

## Contributing

1. Follow code style guidelines
2. Add comprehensive docstrings
3. Write unit tests
4. Update documentation 
