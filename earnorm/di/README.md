# Dependency Injection Module

## Overview
The DI module provides a powerful dependency injection system for EarnORM, enabling loose coupling, better testability, and lifecycle management of services.

## Structure

```
di/
├── container/     # Service container implementation
│   ├── base.py    # Base container functionality
│   ├── service.py # Service definitions
│   ├── factory.py # Service factory
│   └── interfaces.py # Container interfaces
├── lifecycle/     # Service lifecycle management
│   ├── manager.py # Lifecycle manager
│   └── events.py  # Lifecycle events
└── resolver/      # Dependency resolution
    └── dependency.py # Dependency resolver
```

## Components

### 1. Service Container
Core container for managing services and dependencies:

```python
from earnorm.di import Container, service

# Create container
container = Container()

# Define service
@service
class DatabaseService:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

# Register service
container.register(
    "database",
    DatabaseService,
    host="localhost",
    port=27017
)

# Get service
db = container.get("database")
```

### 2. Service Factory
Factory pattern for creating services:

```python
from earnorm.di import ServiceFactory, Provider

class DatabaseProvider(Provider):
    async def provide(self, container):
        return await Database.connect(
            host=container.config.get("DB_HOST"),
            port=container.config.get("DB_PORT")
        )

# Create factory
factory = ServiceFactory()
factory.register("database", DatabaseProvider())

# Create service
db = await factory.create("database", container)
```

### 3. Lifecycle Management
Manage service initialization and cleanup:

```python
from earnorm.di import LifecycleManager, lifecycle

class Cache:
    @lifecycle.on_init
    async def initialize(self):
        await self.connect()
    
    @lifecycle.on_shutdown
    async def cleanup(self):
        await self.disconnect()

# Create manager
manager = LifecycleManager()

# Register service
manager.register(Cache())

# Start/stop services
await manager.start()
await manager.stop()
```

### 4. Dependency Resolution
Automatic dependency injection and resolution:

```python
from earnorm.di import inject, Inject

class UserService:
    # Constructor injection
    @inject
    def __init__(self, database: Inject[Database]):
        self.db = database
    
    # Method injection
    @inject
    async def get_user(self, cache: Inject[Cache]):
        # Check cache first
        user = await cache.get(f"user:{id}")
        if not user:
            user = await self.db.find_one("users", {"id": id})
            await cache.set(f"user:{id}", user)
        return user
```

## Configuration

### 1. Basic Setup
```python
from earnorm.di import setup_container

# Create container
container = setup_container()

# Register services
container.register("database", Database)
container.register("cache", Cache)
container.register("events", EventBus)

# Configure services
container.configure({
    "database": {
        "host": "localhost",
        "port": 27017
    },
    "cache": {
        "url": "redis://localhost"
    }
})
```

### 2. With Providers
```python
from earnorm.di import setup_container, Provider

class ConfigProvider(Provider):
    async def provide(self, container):
        return {
            "env": "development",
            "debug": True
        }

# Setup with providers
container = setup_container([
    DatabaseProvider(),
    CacheProvider(),
    ConfigProvider()
])
```

## Best Practices

1. **Service Design**
- Keep services focused and single-purpose
- Use interfaces for abstraction
- Follow dependency inversion principle
- Design for testability

2. **Dependency Management**
- Use constructor injection when possible
- Avoid circular dependencies
- Keep dependency graph shallow
- Document service requirements

3. **Lifecycle Management**
- Initialize services in correct order
- Handle cleanup properly
- Monitor service health
- Log lifecycle events

4. **Configuration**
- Use environment variables
- Implement configuration validation
- Support multiple environments
- Document configuration options

## Common Issues & Solutions

1. **Circular Dependencies**
- Use lazy loading
- Inject factories instead of instances
- Break cycles with events
- Refactor service boundaries

2. **Resource Management**
- Implement proper cleanup
- Handle initialization failures
- Monitor resource usage
- Use timeouts appropriately

3. **Testing**
- Use mock services
- Create test containers
- Isolate tests
- Mock external dependencies

## Contributing

1. Follow code style guidelines
2. Add comprehensive docstrings
3. Write unit tests
4. Update documentation 
