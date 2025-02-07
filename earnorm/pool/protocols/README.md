# Pool Protocols

This module provides protocol definitions for connection pooling in the EarnORM framework.

## Overview

The protocols module defines interfaces and protocols for:

1. Pool Protocol (`pool.py`)
   - Connection acquisition
   - Connection release
   - Pool lifecycle
   - Health checks

## Features

### 1. Pool Protocol
```python
from typing import AsyncContextManager, TypeVar, Generic
from earnorm.pool.protocols import AsyncPoolProtocol

T = TypeVar("T")

class CustomPool(AsyncPoolProtocol[T]):
    """Custom pool implementation.
    
    Examples:
        >>> pool = CustomPool(uri="custom://localhost:1234")
        >>> async with pool.acquire() as conn:
        ...     # Use connection
        ...     pass
    """
    
    async def acquire(self) -> AsyncContextManager[T]:
        """Acquire a connection from the pool.
        
        Examples:
            >>> async with pool.acquire() as conn:
            ...     # Use connection
            ...     pass
        """
        ...
        
    async def release(self, conn: T) -> None:
        """Release a connection back to the pool.
        
        Examples:
            >>> conn = await pool.get()
            >>> try:
            ...     # Use connection
            ...     pass
            ... finally:
            ...     await pool.release(conn)
        """
        ...
        
    async def init(self) -> None:
        """Initialize the pool.
        
        Examples:
            >>> pool = CustomPool(uri="custom://localhost:1234")
            >>> await pool.init()
        """
        ...
        
    async def close(self) -> None:
        """Close the pool.
        
        Examples:
            >>> await pool.close()
        """
        ...
```

## Implementation Guide

### 1. Creating Pool Implementation

1. Basic implementation:
```python
from typing import AsyncContextManager, TypeVar
from contextlib import asynccontextmanager
from earnorm.pool.protocols import AsyncPoolProtocol

T = TypeVar("T")

class CustomPool(AsyncPoolProtocol[T]):
    def __init__(self, uri: str):
        self.uri = uri
        self._pool = []
        
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[T]:
        conn = await self.get()
        try:
            yield conn
        finally:
            await self.release(conn)
            
    async def get(self) -> T:
        if not self._pool:
            return await self._create_connection()
        return self._pool.pop()
        
    async def release(self, conn: T) -> None:
        self._pool.append(conn)
        
    async def init(self) -> None:
        # Initialize pool
        ...
        
    async def close(self) -> None:
        # Close all connections
        ...
```

2. Advanced implementation:
```python
class AdvancedPool(AsyncPoolProtocol[T]):
    def __init__(self, uri: str, **options):
        self.uri = uri
        self.options = options
        self._pool = []
        self._in_use = set()
        self._closed = False
        
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[T]:
        conn = await self.get()
        try:
            yield conn
        finally:
            await self.release(conn)
            
    async def get(self) -> T:
        if self._closed:
            raise PoolClosedError()
            
        if not self._pool:
            conn = await self._create_connection()
        else:
            conn = self._pool.pop()
            
        self._in_use.add(conn)
        return conn
        
    async def release(self, conn: T) -> None:
        self._in_use.remove(conn)
        self._pool.append(conn)
        
    async def init(self) -> None:
        # Create initial connections
        for _ in range(self.min_size):
            conn = await self._create_connection()
            self._pool.append(conn)
            
    async def close(self) -> None:
        self._closed = True
        
        # Close all connections
        for conn in self._pool:
            await self._destroy_connection(conn)
        self._pool.clear()
        
        for conn in self._in_use:
            await self._destroy_connection(conn)
        self._in_use.clear()
```

### 2. Using Pool Protocol

1. Type hints:
```python
from typing import TypeVar, AsyncContextManager
from earnorm.pool.protocols import AsyncPoolProtocol

T = TypeVar("T")

async def use_pool(pool: AsyncPoolProtocol[T]) -> None:
    async with pool.acquire() as conn:
        # Use connection
        ...
```

2. Protocol validation:
```python
from typing import runtime_checkable, Protocol

@runtime_checkable
class ConnectionProtocol(Protocol):
    async def query(self, sql: str) -> None:
        ...
        
    async def close(self) -> None:
        ...

# Pool with specific connection type
class DatabasePool(AsyncPoolProtocol[ConnectionProtocol]):
    ...
```

## Best Practices

1. Protocol Design
   - Clear interfaces
   - Type safety
   - Error handling
   - Resource cleanup
   - Documentation

2. Implementation
   - Follow protocol
   - Handle errors
   - Clean resources
   - Type hints
   - Documentation

3. Usage
   - Context managers
   - Type checking
   - Error handling
   - Resource cleanup
   - Proper initialization

4. Testing
   - Protocol compliance
   - Error cases
   - Resource cleanup
   - Type safety
   - Documentation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
