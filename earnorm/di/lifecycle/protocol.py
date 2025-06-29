"""Lifecycle protocol module for dependency injection.

This module defines the protocol that objects must implement to be lifecycle-aware.
The protocol requires:

1. Initialization:
   - Async initialization method
   - Resource allocation
   - State setup
   - Dependency injection

2. Destruction:
   - Async cleanup method
   - Resource release
   - State cleanup
   - Connection closing

3. Identification:
   - Unique identifier
   - Object metadata
   - State information
   - Debug data

Example:
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
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LifecycleAware(Protocol):
    """Protocol for lifecycle-aware objects.

    This protocol defines the interface that objects must implement
    to participate in lifecycle management. It includes methods for:
    - Initialization
    - Destruction
    - Identification
    - State tracking

    Example:
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
    """

    async def init(self) -> None:
        """Initialize the object.

        This method should:
        1. Allocate required resources
        2. Set up initial state
        3. Inject dependencies
        4. Establish connections

        Raises:
            InitializationError: If initialization fails
            ResourceError: If resource allocation fails
            ConnectionError: If connection establishment fails
        """
        ...

    async def destroy(self) -> None:
        """Destroy the object and cleanup resources.

        This method should:
        1. Release allocated resources
        2. Close connections
        3. Clean up state
        4. Remove event handlers

        Raises:
            DestructionError: If destruction fails
            ResourceError: If resource cleanup fails
            ConnectionError: If connection closing fails
        """
        ...

    @property
    def id(self) -> str | None:
        """Get object identifier.

        This property should return a unique identifier for the object.
        The identifier is used for:
        - Object tracking
        - Event routing
        - Logging
        - Debugging

        Returns:
            Unique identifier string or None if not available
        """
        ...

    @property
    def data(self) -> dict[str, str]:
        """Get object data.

        This property should return a dictionary containing:
        - Object state information
        - Resource status
        - Connection details
        - Debug information

        Returns:
            Dictionary mapping data keys to string values
        """
        ...
