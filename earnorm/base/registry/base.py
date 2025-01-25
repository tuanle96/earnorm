"""Registry base classes.

This module provides base classes and interfaces for registries.
It defines the contract that all registries must implement.

Examples:
    ```python
    from earnorm.registry.base import Registry
    from earnorm.di.lifecycle import LifecycleAware
    from earnorm.config import SystemConfig

    class MyRegistry(Registry[MyService]):
        async def register(self, name: str, service: Type[MyService], config: SystemConfig) -> None:
            # Configure service with system config
            service.configure(
                host=config.redis_host,
                port=config.redis_port
            )
            # Register service
            await self._container.register(name, service)
    ```
"""

from abc import ABC, abstractmethod
from typing import Any, Coroutine, Dict, Generic, Optional, Type, TypeVar

from earnorm.di import container
from earnorm.di.lifecycle import LifecycleAware

T = TypeVar("T", bound=LifecycleAware)


class Registry(ABC, Generic[T], LifecycleAware):
    """Abstract registry interface.

    This class defines the interface for registries that manage lifecycle-aware instances.
    It provides methods for registration, retrieval, and lifecycle management.

    Examples:
        ```python
        class MyRegistry(Registry[MyService]):
            async def register(self, name: str, service: Type[MyService]) -> None:
                await self._container.register(name, service)

            async def get(self, name: str) -> MyService:
                return await self._container.get(name)
        ```
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._container = container
        self._options: Dict[str, Dict[str, Any]] = {}
        self._default: Optional[str] = None
        self._caches: Dict[str, Dict[str, Any]] = {}
        self._connection: Any = None

    @property
    @abstractmethod
    def id(self) -> str:
        """Get registry ID."""
        pass

    @property
    @abstractmethod
    def data(self) -> Dict[str, Any]:
        """Get registry data."""
        pass

    @abstractmethod
    async def register(self, name: str, instance: Type[T], **options: Any) -> None:
        """Register instance.

        Args:
            name: Instance name
            instance: Instance class
            **options: Instance options

        Examples:
            ```python
            await registry.register("mongodb", MongoBackend, uri="mongodb://localhost")
            ```
        """
        pass

    @abstractmethod
    async def unregister(self, name: str) -> None:
        """Unregister instance.

        Args:
            name: Instance name

        Examples:
            ```python
            await registry.unregister("mongodb")
            ```
        """
        pass

    @abstractmethod
    def get(self, name: Optional[str] = None) -> Coroutine[Any, Any, T]:
        """Get instance.

        Args:
            name: Instance name (optional)

        Returns:
            Coroutine returning instance of type T

        Examples:
            ```python
            backend = await registry.get("mongodb")
            ```
        """
        pass

    @abstractmethod
    async def switch(self, name: str, **options: Any) -> None:
        """Switch to different instance.

        Args:
            name: Instance name
            **options: Instance options

        Examples:
            ```python
            await registry.switch("postgres", host="localhost", port=5432)
            ```
        """
        pass

    async def has(self, name: str) -> bool:
        """Check if instance exists.

        Args:
            name: Instance name

        Returns:
            True if instance exists

        Examples:
            ```python
            if await registry.has("mongodb"):
                backend = await registry.get("mongodb")
            ```
        """
        return name in self._options

    async def set_default(self, name: str) -> None:
        """Set default instance.

        Args:
            name: Instance name

        Examples:
            ```python
            await registry.set_default("mongodb")
            ```
        """
        if name not in self._options:
            raise ValueError(f"Unknown instance: {name}")
        self._default = name

    async def get_default(self) -> Optional[str]:
        """Get default instance name.

        Returns:
            Default instance name

        Examples:
            ```python
            default = await registry.get_default()
            ```
        """
        return self._default

    def get_connection(self) -> Any:
        """Get database connection.

        Returns:
            Database connection

        Raises:
            RuntimeError: If connection not initialized

        Examples:
            ```python
            conn = registry.get_connection()
            # Do something with connection
            ```
        """
        if not self._connection:
            raise RuntimeError("Connection not initialized")
        return self._connection

    def get_backend_type(self) -> str:
        """Get current backend type.

        Returns:
            Backend type name (e.g. "mongodb", "postgres")

        Raises:
            RuntimeError: If no backend is set
        """
        if not self._default:
            raise RuntimeError("No backend set")
        return self._default

    async def clear_caches(self) -> None:
        """Clear all caches."""
        self._caches.clear()
