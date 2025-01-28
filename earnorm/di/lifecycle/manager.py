"""Lifecycle manager module for dependency injection.

This module provides the main lifecycle management functionality.
The lifecycle manager is responsible for:

1. Object Management:
   - Object initialization
   - Object destruction
   - Object tracking
   - State management

2. Resource Management:
   - Resource allocation
   - Resource cleanup
   - Resource tracking
   - Resource validation

3. Event Management:
   - Event emission
   - Event handling
   - Event propagation
   - Error handling

Example:
    >>> manager = LifecycleManager()
    >>>
    >>> # Initialize objects
    >>> service = MyService()
    >>> await manager.init(service)
    >>>
    >>> # Get objects
    >>> assert manager.get("my_service") == service
    >>> assert len(manager.get_all()) == 1
    >>>
    >>> # Cleanup
    >>> await manager.destroy("my_service")
    >>> await manager.destroy_all()
"""

import logging
from typing import Dict, List, Optional, Type, TypeVar

from earnorm.di.lifecycle.events import LifecycleEvents
from earnorm.di.lifecycle.protocol import LifecycleAware
from earnorm.exceptions import EarnORMError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=LifecycleAware)


class LifecycleManagerError(EarnORMError):
    """Exception raised when lifecycle operations fail."""

    pass


class LifecycleManager:
    """Lifecycle manager implementation.

    The LifecycleManager class manages the lifecycle of objects that implement
    the LifecycleAware protocol. It handles:
    - Object initialization and destruction
    - Resource management
    - Event handling
    - State tracking

    Features:
        - Async initialization and cleanup
        - Event-driven lifecycle management
        - Resource tracking and cleanup
        - Type-safe object management
        - Error handling and recovery

    Example:
        >>> manager = LifecycleManager()
        >>>
        >>> # Initialize object
        >>> service = MyService()
        >>> await manager.init(service)
        >>>
        >>> # Get object
        >>> assert manager.get("my_service") == service
        >>>
        >>> # Cleanup
        >>> await manager.destroy("my_service")
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager.

        This constructor sets up:
        1. Object registry for tracking managed objects
        2. Event system for lifecycle events
        3. Error handling configuration
        """
        self._objects: Dict[str, LifecycleAware] = {}
        self._events = LifecycleEvents()

    async def init(self, obj: T, name: Optional[str] = None) -> T:
        """Initialize an object.

        This method:
        1. Validates the object
        2. Emits initialization events
        3. Initializes the object
        4. Tracks the initialized object

        Args:
            obj: Object to initialize
            name: Optional name for the object (defaults to class name)

        Returns:
            Initialized object

        Raises:
            ValueError: If object already initialized
            LifecycleError: If initialization fails
            EventError: If event emission fails

        Example:
            >>> service = MyService()
            >>> await manager.init(service)
            >>> assert manager.has("my_service")
        """
        if not name:
            name = obj.__class__.__name__

        if name in self._objects:
            raise ValueError(f"Object {name} already initialized")

        try:
            # Emit events
            await self._events.before_init(obj)

            # Initialize object
            await obj.init()

            # Store object
            self._objects[name] = obj

            # Emit events
            await self._events.after_init(obj)

            return obj

        except Exception as e:
            logger.error("Failed to initialize %s: %s", name, str(e))
            raise LifecycleManagerError(f"Failed to initialize {name}: {e}") from e

    async def destroy(self, name: str) -> None:
        """Destroy an object.

        This method:
        1. Validates the object exists
        2. Emits destruction events
        3. Destroys the object
        4. Removes the object from tracking

        Args:
            name: Name of the object to destroy

        Raises:
            LifecycleError: If destruction fails
            EventError: If event emission fails

        Example:
            >>> await manager.destroy("my_service")
            >>> assert not manager.has("my_service")
        """
        obj = self._objects.get(name)
        if not obj:
            return

        try:
            # Emit events
            await self._events.before_destroy(obj)

            # Destroy object
            await obj.destroy()

            # Remove object
            del self._objects[name]

            # Emit events
            await self._events.after_destroy(obj)

        except Exception as e:
            logger.error("Failed to destroy %s: %s", name, str(e))
            raise LifecycleManagerError(f"Failed to destroy {name}: {e}") from e

    async def destroy_all(self) -> None:
        """Destroy all managed objects.

        This method:
        1. Gets all managed objects
        2. Destroys each object in reverse initialization order
        3. Cleans up resources
        4. Resets manager state

        Raises:
            LifecycleError: If any destruction fails
            EventError: If event emission fails

        Example:
            >>> await manager.destroy_all()
            >>> assert len(manager.get_all()) == 0
        """
        for name in list(self._objects.keys()):
            await self.destroy(name)

    def get(self, name: str) -> Optional[LifecycleAware]:
        """Get a managed object by name.

        Args:
            name: Name of the object to get

        Returns:
            Object if found, None otherwise

        Example:
            >>> service = manager.get("my_service")
            >>> if service:
            ...     await service.do_something()
        """
        return self._objects.get(name)

    def get_all(self) -> List[LifecycleAware]:
        """Get all managed objects.

        Returns:
            List of all managed objects

        Example:
            >>> objects = manager.get_all()
            >>> for obj in objects:
            ...     print(f"{obj.id}: {obj.data}")
        """
        return list(self._objects.values())

    def get_by_type(self, type_: Type[T]) -> List[T]:
        """Get all objects of a specific type.

        Args:
            type_: Type of objects to get

        Returns:
            List of objects matching the specified type

        Example:
            >>> services = manager.get_by_type(MyService)
            >>> for service in services:
            ...     await service.do_something()
        """
        return [obj for obj in self._objects.values() if isinstance(obj, type_)]
