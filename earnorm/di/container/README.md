# Container Module

This module provides the core dependency injection container functionality for EarnORM.

## Overview

The container module consists of four main components:

1. Base Container (`base.py`)
2. Service Manager (`service.py`)
3. Factory Manager (`factory.py`)
4. Container Interfaces (`interfaces.py`)

### Base Container

The base container provides the main DI container implementation:

```python
from earnorm.di.container import Container

# Create container
container = Container()

# Register services
container.register("config", SystemConfig())
container.register_factory("database", create_database)

# Get services
config = await container.get("config")
db = await container.get("database")
```

### Service Manager

The service manager handles service registration and lifecycle:

```python
from earnorm.di.container import ServiceManager

# Create manager
manager = ServiceManager()

# Register services
manager.register("config", SystemConfig())
manager.register("database", Database, "transient")

# Get services
config = await manager.get("config")
db = await manager.get("database")
```

### Factory Manager

The factory manager handles factory-based service creation:

```python
from earnorm.di.container import FactoryManager

# Create manager
manager = FactoryManager()

# Register factory
def create_database(config: SystemConfig) -> Database:
    return Database(config.database_uri)

manager.register("database", create_database)

# Create instance
db = await manager.get("database")
```

## Features

### 1. Service Management

- Service registration with lifecycles
- Singleton and transient services
- Service initialization
- Instance caching
- Resource cleanup

### 2. Factory Support

- Factory function registration
- Factory-based instance creation
- Async factory support
- Factory configuration
- Factory validation

### 3. Dependency Resolution

- Service dependency tracking
- Circular dependency detection
- Dependency order resolution
- Dependency validation

### 4. Lifecycle Management

- Service initialization
- Resource cleanup
- Event handling
- State management

## Implementation Guide

### 1. Using the Container

```python
# Create container
container = Container()

# Initialize with config
config = SystemConfig()
await container.init(config)

# Register services
container.register("service", MyService())
container.register_factory("factory", create_service)

# Get services
service = await container.get("service")
factory = await container.get("factory")
```

### 2. Creating Services

```python
# Singleton service
class ConfigService:
    def __init__(self):
        self.config = {}

container.register("config", ConfigService())

# Transient service
class DatabaseConnection:
    def __init__(self):
        self.connection = None

container.register("database", DatabaseConnection, "transient")
```

### 3. Using Factories

```python
# Create factory function
async def create_database(config: SystemConfig) -> Database:
    db = Database(config.database_uri)
    await db.connect()
    return db

# Register factory
container.register_factory("database", create_database)

# Get instance
db = await container.get("database")
```

## Best Practices

1. Service Registration
- Use descriptive service names
- Document service dependencies
- Handle initialization errors
- Clean up resources

2. Factory Usage
- Keep factories focused
- Handle async initialization
- Validate factory output
- Document factory requirements

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

This project is licensed under the MIT License - see the LICENSE file for details. 
