"""EarnORM application."""

from typing import Any, Type

from motor.motor_asyncio import AsyncIOMotorClient

from earnorm.base.model import BaseModel
from earnorm.base.registry import Registry
from earnorm.di.container import DIContainer


class EarnORMApp(DIContainer):
    """EarnORM application.

    This class manages the application lifecycle and provides access to core services.
    """

    def __init__(self) -> None:
        """Initialize application."""
        super().__init__()
        self.registry = Registry()
        self.register("registry", self.registry)

    def register_model(self, model: Type[BaseModel]) -> None:
        """Register model.

        Args:
            model: Model class to register
        """
        self.registry.register_model(model)

    async def init_resources(
        self, *, mongo_uri: str, database: str, **kwargs: Any
    ) -> None:
        """Initialize application resources.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            **kwargs: Additional configuration
        """
        # Initialize database
        client = AsyncIOMotorClient[Any](mongo_uri)
        db = client[database]
        await self.registry.init_db(db)

    async def cleanup(self) -> None:
        """Cleanup application resources."""
        # Close database connection
        if self.registry.db is not None:
            client = self.registry.db.client
            if client.is_alive():
                client.close()


# Global application instance
app = EarnORMApp()

# Expose commonly used instances
registry = app.registry
env = registry  # Odoo-style env alias
