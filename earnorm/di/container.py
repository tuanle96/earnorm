"""Dependency injection container."""

import logging
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from earnorm.base.registry import Registry
from earnorm.di.lifecycle import LifecycleManager

logger = logging.getLogger(__name__)


@runtime_checkable
class Container(Protocol):
    """Container protocol."""

    async def init(self, **kwargs: Any) -> None:
        """Initialize container."""
        ...

    async def init_resources(
        self, *, mongo_uri: str, database: str, **kwargs: Any
    ) -> None:
        """Initialize container resources."""
        ...

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        ...

    def get(self, key: str) -> Any:
        """Get service by key."""
        ...

    def register(self, key: str, service: Any) -> None:
        """Register service."""
        ...


class DIContainer:
    """EarnORM dependency injection container."""

    _instance: Optional["DIContainer"] = None
    _registry: Optional[Registry] = None
    _lifecycle: Optional[LifecycleManager] = None

    def __new__(cls) -> "DIContainer":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize container."""
        if not getattr(self, "_initialized", False):
            self._services: Dict[str, Any] = {}
            self._client: AsyncIOMotorClient[Dict[str, Any]] | None = None
            self._db: AsyncIOMotorDatabase[Dict[str, Any]] | None = None
            self._initialized = True

            # Initialize services
            if DIContainer._registry is None:
                DIContainer._registry = Registry()
            if DIContainer._lifecycle is None:
                DIContainer._lifecycle = LifecycleManager()

            self._services["registry"] = DIContainer._registry
            self._services["lifecycle"] = DIContainer._lifecycle

    async def init(self, **kwargs: Any) -> None:
        """Initialize container."""
        await self.init_resources(**kwargs)

    async def init_resources(
        self, *, mongo_uri: str, database: str, **kwargs: Any
    ) -> None:
        """Initialize container resources."""
        logger.info("Connecting to MongoDB: %s", mongo_uri)
        try:
            self._client = AsyncIOMotorClient(mongo_uri)
            # Test connection
            await self._client.admin.command("ping")
            logger.info("Connected to MongoDB successfully")

            self._db = self._client[database]
            self._services["db"] = self._db
            logger.info("Using database: %s", database)

            # Initialize registry with database
            registry = self._services["registry"]
            await registry.init_db(self._db)
            logger.info("Registry initialized with database")
        except Exception as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            raise

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    def get(self, key: str) -> Any:
        """Get service by key."""
        return self._services[key]

    def register(self, key: str, service: Any) -> None:
        """Register service."""
        self._services[key] = service

    def get_lifecycle(self) -> LifecycleManager:
        """Get lifecycle manager."""
        return self._services["lifecycle"]


__all__ = ["Container", "DIContainer"]
