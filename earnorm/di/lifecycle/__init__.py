"""Lifecycle management module for dependency injection.

This module provides lifecycle management functionality for the DI system.
It includes:

1. Lifecycle Protocol:
   - Initialization interface
   - Destruction interface
   - State management
   - Resource tracking

2. Event System:
   - Lifecycle event emission
   - Event handling
   - Event propagation
   - Event filtering

3. Lifecycle Management:
   - Object initialization
   - Resource cleanup
   - State tracking
   - Error handling

Example:
    >>> from earnorm.di.lifecycle import LifecycleAware, LifecycleManager
    >>>
    >>> class MyService(LifecycleAware):
    ...     async def init(self) -> None:
    ...         # Initialize resources
    ...         pass
    ...
    ...     async def destroy(self) -> None:
    ...         # Cleanup resources
    ...         pass
    ...
    ...     @property
    ...     def id(self) -> str:
    ...         return "my_service"
    ...
    ...     @property
    ...     def data(self) -> Dict[str, str]:
    ...         return {"status": "running"}
    >>>
    >>> # Create and initialize service
    >>> manager = LifecycleManager()
    >>> service = MyService()
    >>> await manager.init(service)
"""

from earnorm.di.lifecycle.events import EventError, LifecycleEvents
from earnorm.di.lifecycle.manager import LifecycleAware, LifecycleManager

__all__ = ["EventError", "LifecycleAware", "LifecycleEvents", "LifecycleManager"]
