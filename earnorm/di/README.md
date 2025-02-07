# Dependency Injection Module

This module provides a comprehensive dependency injection system for the EarnORM framework. It consists of two main components: Container and Lifecycle management.

## Overview

The DI module consists of three main components:

1. Container System (`container/`)
2. Lifecycle System (`lifecycle/`)
3. Service Management (`service/`)

## Directory Structure

```
di/
├── __init__.py         # Package exports
├── container/          # DI container implementation
│   ├── __init__.py
│   ├── base.py        # Base container class
│   ├── factory.py     # Factory manager
│   ├── service.py     # Service manager
│   └── interfaces.py  # Container interfaces
├── lifecycle/         # Lifecycle management
│   ├── __init__.py
│   ├── events.py     # Event system
│   ├── manager.py    # Lifecycle manager
│   └── protocol.py   # Lifecycle protocol
└── service/          # Service management
    ├── __init__.py
    ├── base.py       # Base service class
    └── manager.py    # Service manager
```

## Key Features

### 1. Container System
```python
from earnorm.di.container import Container
from earnorm.config import SystemConfig

# Create container
container = Container()

# Register services
container.register("config", SystemConfig())
container.register_factory("database", create_database)

# Get services
config = await container.get("config")
db = await container.get("database")
```

### 2. Lifecycle Management
```python
from earnorm.di.lifecycle import LifecycleAware, LifecycleManager

class MyService(LifecycleAware):
    async def init(self) -> None:
        self._connection = await create_connection()
        self._state = "initialized"

    async def destroy(self) -> None:
        await self._connection.close()
        self._state = "destroyed"

    @property
    def id(self) -> str:
        return "my_service"

# Use lifecycle manager
manager = LifecycleManager()
service = MyService()
await manager.init(service)
```

### 3. Service Management
```python
from earnorm.di.service import ServiceManager

# Create manager
manager = ServiceManager()

# Register services
manager.register("config", SystemConfig())
manager.register("database", Database, "transient")

# Get services
config = await manager.get("config")
db = await manager.get("database")
```

## Features

1. Container System
   - Service registration and retrieval
   - Factory registration and management
   - Lifecycle management
   - Dependency resolution
   - Circular dependency detection

2. Lifecycle Management
   - Object lifecycle tracking
   - Resource management
   - Event handling
   - State management
   - Error recovery

3. Service Management
   - Service registration
   - Dependency injection
   - Lifecycle hooks
   - Resource cleanup
   - Error handling

## Implementation Guide

### 1. Using the Container

1. Create and initialize container:
```python
container = Container()
config = SystemConfig()
await container.init(config)
```

2. Register services:
```python
# Register singleton
container.register("config", SystemConfig())

# Register transient service
container.register("database", Database, "transient")

# Register factory
container.register_factory("connection", create_connection)
```

3. Get services:
```python
# Get singleton
config = await container.get("config")

# Get new instance
db = await container.get("database")

# Get from factory
conn = await container.get("connection")
```

### 2. Using Lifecycle Management

1. Create lifecycle-aware objects:
```python
class MyService(LifecycleAware):
    async def init(self) -> None:
        # Initialize resources
        pass

    async def destroy(self) -> None:
        # Cleanup resources
        pass
```

2. Manage object lifecycle:
```python
manager = LifecycleManager()

# Initialize
service = MyService()
await manager.init(service)

# Get managed object
obj = manager.get("my_service")

# Cleanup
await manager.destroy("my_service")
```

### 3. Using Service Management

1. Create service manager:
```python
manager = ServiceManager()
```

2. Register services:
```python
# Register singleton
manager.register("config", SystemConfig())

# Register with factory
manager.register_factory("database", create_database)
```

3. Get services:
```python
# Get singleton
config = await manager.get("config")

# Get from factory
db = await manager.get("database")
```

## Best Practices

1. Service Registration
   - Use descriptive service names
   - Document service dependencies
   - Handle initialization errors
   - Clean up resources properly

2. Lifecycle Management
   - Implement proper resource cleanup
   - Handle initialization errors
   - Use event system appropriately
   - Track object state clearly

3. Dependency Management
   - Avoid circular dependencies
   - Use dependency injection
   - Document dependencies
   - Handle missing dependencies

4. Error Handling
   - Use custom exceptions
   - Provide error context
   - Log initialization errors
   - Handle cleanup errors

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
