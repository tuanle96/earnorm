"""Lifecycle management module for EarnORM.

This module provides a comprehensive system for managing object lifecycles
in the EarnORM framework. It includes:

1. Lifecycle Protocol:
   - Interface for lifecycle-aware objects
   - Initialization and destruction methods
   - State tracking and identification
   - Resource management

2. Event System:
   - Lifecycle event handling
   - Event subscription and emission
   - Error handling and propagation
   - Event-driven architecture

3. Lifecycle Manager:
   - Object lifecycle management
   - Resource allocation and cleanup
   - Object tracking and retrieval
   - Error handling and recovery

Key Features:
    - Async initialization and destruction
    - Resource tracking and cleanup
    - Event-driven lifecycle management
    - Type-safe object management
    - Error handling and recovery

Example:
    >>> from earnorm.di.lifecycle import LifecycleAware, LifecycleManager
    >>>
    >>> class MyService(LifecycleAware):
    ...     async def init(self) -> None:
    ...         self._connection = await create_connection()
    ...         self._state = "initialized"
    ...
    ...     async def destroy(self) -> None:
    ...         await self._connection.close()
    ...         self._state = "destroyed"
    ...
    ...     @property
    ...     def id(self) -> str:
    ...         return "my_service"
    ...
    ...     @property
    ...     def data(self) -> Dict[str, str]:
    ...         return {
    ...             "state": self._state,
    ...             "connection": str(self._connection)
    ...         }
    >>>
    >>> # Create manager and initialize service
    >>> manager = LifecycleManager()
    >>> service = MyService()
    >>> await manager.init(service)
    >>>
    >>> # Use service
    >>> assert manager.get("my_service") == service
    >>>
    >>> # Cleanup
    >>> await manager.destroy("my_service")

See Also:
    - earnorm.di.container: Container module for dependency injection
    - earnorm.di.factory: Factory module for object creation
    - earnorm.di.service: Service module for dependency management
"""

from earnorm.di.lifecycle.events import LifecycleEvents
from earnorm.di.lifecycle.manager import LifecycleManager
from earnorm.di.lifecycle.protocol import LifecycleAware

__all__ = [
    "LifecycleAware",  # Protocol for lifecycle-aware objects
    "LifecycleEvents",  # Event system for lifecycle management
    "LifecycleManager",  # Manager for lifecycle operations
]
