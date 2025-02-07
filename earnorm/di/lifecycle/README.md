# Lifecycle Module

The Lifecycle module provides a robust system for managing object lifecycles in the EarnORM framework. It handles initialization, destruction, resource management, and event handling for objects that implement the lifecycle protocol.

## Overview

The module consists of four main components:

1. **Protocol System** (`protocol.py`):
   - Defines the `LifecycleAware` protocol for lifecycle-aware objects
   - Specifies required methods for initialization and destruction
   - Provides identification and state tracking interfaces

2. **Event System** (`events.py`):
   - Manages lifecycle events (initialization, destruction)
   - Handles event subscription and emission
   - Provides error handling and event propagation

3. **Manager System** (`manager.py`):
   - Implements the `LifecycleManager` for object lifecycle management
   - Handles object initialization and destruction
   - Manages resource allocation and cleanup
   - Provides object tracking and retrieval

4. **Core Module** (`__init__.py`):
   - Exports main components and interfaces
   - Provides high-level lifecycle management functionality
   - Defines module-level configuration

## Key Features

### 1. Lifecycle Protocol
```python
from earnorm.di.lifecycle import LifecycleAware

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

    @property
    def data(self) -> Dict[str, str]:
        return {
            "state": self._state,
            "connection": str(self._connection)
        }
```

### 2. Lifecycle Management
```python
from earnorm.di.lifecycle import LifecycleManager

# Create manager
manager = LifecycleManager()

# Initialize object
service = MyService()
await manager.init(service)

# Get managed object
assert manager.get("my_service") == service

# Cleanup
await manager.destroy("my_service")
await manager.destroy_all()
```

### 3. Event Handling
```python
from earnorm.di.lifecycle import LifecycleEvents

events = LifecycleEvents()

# Subscribe to events
async def on_init(obj: LifecycleAware) -> None:
    print(f"Initializing {obj.id}")

events.subscribe_init(on_init)

# Events are automatically emitted by LifecycleManager
```

## Implementation Guide

### 1. Creating Lifecycle-Aware Objects

1. Implement the `LifecycleAware` protocol:
   - `init()`: Initialize resources and state
   - `destroy()`: Cleanup resources and state
   - `id`: Unique object identifier
   - `data`: Object state information

2. Handle initialization properly:
   - Allocate resources safely
   - Set up initial state
   - Establish connections
   - Handle errors appropriately

3. Implement proper cleanup:
   - Release resources in reverse order
   - Close connections
   - Clean up state
   - Remove event handlers

### 2. Using the Lifecycle Manager

1. Create a manager instance:
   ```python
   manager = LifecycleManager()
   ```

2. Initialize objects:
   ```python
   service = MyService()
   await manager.init(service, name="custom_name")  # name is optional
   ```

3. Manage objects:
   ```python
   # Get object by name
   obj = manager.get("my_service")
   
   # Get all objects
   all_objects = manager.get_all()
   
   # Get objects by type
   services = manager.get_by_type(MyService)
   ```

4. Cleanup:
   ```python
   # Destroy single object
   await manager.destroy("my_service")
   
   # Destroy all objects
   await manager.destroy_all()
   ```

## Best Practices

1. **Resource Management**:
   - Always release resources in reverse order of acquisition
   - Use context managers when possible
   - Handle cleanup errors gracefully

2. **Error Handling**:
   - Catch and handle initialization errors
   - Implement proper cleanup in error cases
   - Log errors with appropriate context

3. **Event Usage**:
   - Keep event handlers lightweight
   - Handle event errors properly
   - Avoid circular event dependencies

4. **State Management**:
   - Track object state clearly
   - Validate state transitions
   - Provide clear state information

## Contributing

1. Follow the EarnORM coding standards
2. Add tests for new functionality
3. Update documentation as needed
4. Submit pull requests for review

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
