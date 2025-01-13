"""Dependency injection container for EarnORM."""

from typing import Any, Mapping, Protocol, runtime_checkable

from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from earnorm.base.core.registry import Registry
from earnorm.security.acl import ACLManager
from earnorm.security.audit import AuditManager
from earnorm.security.rbac import RBACManager


@runtime_checkable
class AsyncManager(Protocol):
    """Protocol for async managers."""

    async def init(self) -> None:
        """Initialize manager."""
        ...

    async def cleanup(self) -> None:
        """Cleanup manager resources."""
        ...


class SecurityManager(AsyncManager):
    """Base class for security managers."""

    async def init(self) -> None:
        """Initialize manager."""
        ...

    async def cleanup(self) -> None:
        """Cleanup manager resources."""
        ...


def get_database(
    client: AsyncIOMotorClient[dict[str, Any]], database: str
) -> AsyncIOMotorDatabase[dict[str, Any]]:
    """Get database from client.

    Args:
        client: Motor client
        database: Database name

    Returns:
        Motor database
    """
    return client[database]


class EarnORMContainer(containers.DeclarativeContainer):
    """Global container for EarnORM dependencies.

    This container manages all global instances and services used throughout
    the application. It provides a centralized way to manage dependencies
    and their lifecycles.

    Example:
        ```python
        from earnorm.di import container

        # Initialize container
        await container.init_resources(
            mongo_uri="mongodb://localhost:27017",
            database="myapp"
        )

        # Access services
        db = container.db()
        registry = container.registry()
        acl = container.acl_manager()
        ```
    """

    # Configuration
    config: providers.Configuration = providers.Configuration()

    # Database
    mongo_client: providers.Singleton[AsyncIOMotorClient[dict[str, Any]]] = (
        providers.Singleton(AsyncIOMotorClient[dict[str, Any]], config.mongo_uri)
    )

    db: providers.Singleton[AsyncIOMotorDatabase[dict[str, Any]]] = providers.Singleton(
        get_database, client=mongo_client, database=config.database
    )

    # Core services
    registry: providers.Singleton[Registry] = providers.Singleton(Registry)

    # Security services
    acl_manager: providers.Singleton[ACLManager] = providers.Singleton(
        ACLManager, db=db, registry=registry
    )

    rbac_manager: providers.Singleton[RBACManager] = providers.Singleton(
        RBACManager, db=db, registry=registry
    )

    audit_manager: providers.Singleton[AuditManager] = providers.Singleton(
        AuditManager, db=db
    )

    async def init_earnorm(
        self,
        *,  # Force keyword arguments
        mongo_uri: str,
        database: str,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize EarnORM container resources.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            config: Additional configuration options
        """
        # Update config
        self.config.from_dict(
            {"mongo_uri": mongo_uri, "database": database, **(config or {})}
        )

        # Initialize database
        db = self.db()
        await self.registry().init_db(db)

        # Initialize security services
        await self.acl_manager().init()
        await self.rbac_manager().init()
        await self.audit_manager().init()

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        # Close database connection
        if self.mongo_client().is_alive():
            self.mongo_client().close()

        # Cleanup managers
        await self.acl_manager().cleanup()
        await self.rbac_manager().cleanup()
        await self.audit_manager().cleanup()


# Global container instance
container = EarnORMContainer()

# Expose commonly used instances
registry = container.registry
env = registry  # Odoo-style env alias
