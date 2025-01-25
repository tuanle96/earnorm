"""Database registry implementation.

This module provides the implementation of database registry.
It manages database backends and their lifecycle.

The registry supports multiple database backends:
- MongoDB: Default backend using Motor
- PostgreSQL: Using asyncpg
- MySQL: Using aiomysql

Examples:
    ```python
    from earnorm.registry import DatabaseRegistry
    from earnorm.base.database.backends import MongoBackend, PostgresBackend

    # Create registry instance
    registry = DatabaseRegistry()

    # Register MongoDB backend
    await registry.register(
        "mongodb",
        MongoBackend,
        uri="mongodb://localhost:27017",
        database="test"
    )

    # Register PostgreSQL backend
    await registry.register(
        "postgres",
        PostgresBackend,
        host="localhost",
        port=5432,
        database="test",
        user="postgres"
    )

    # Get default backend
    backend = await registry.get()

    # Switch between backends
    await registry.switch("postgres")
    ```
"""

from typing import Any, Dict, List, Optional, Type, cast

from earnorm.base.database.backends.base import DatabaseBackend
from earnorm.base.database.backends.mongo import MongoBackend
from earnorm.di import container

from .base import Registry

# Default backend configurations
DEFAULT_BACKENDS: Dict[str, Dict[str, Any]] = {
    "mongodb": {
        "class": MongoBackend,
        "options": {
            "uri": "mongodb://localhost:27017",
            "database": "earnbase",
            "min_pool_size": 5,
            "max_pool_size": 20,
        },
    }
}


class DatabaseRegistry(Registry[DatabaseBackend[Any]]):
    """Database registry implementation.

    This class manages database backends and their lifecycle.
    It supports multiple database types and allows switching between them at runtime.

    Supported backends:
    - MongoDB (default): Using Motor
    - PostgreSQL: Using asyncpg
    - MySQL: Using aiomysql

    Examples:
        ```python
        registry = DatabaseRegistry()

        # Register backend
        await registry.register(
            "mongodb",
            MongoBackend,
            uri="mongodb://localhost:27017",
            database="test"
        )

        # Get backend
        backend = await registry.get("mongodb")
        await backend.connect()

        # Switch backend
        await registry.switch(
            "postgres",
            host="localhost",
            port=5432,
            database="test"
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize registry."""
        super().__init__()
        self._id = "database_registry"
        self._data = {
            "type": "database",
            "description": "Registry for database backends",
            "supported_backends": list(DEFAULT_BACKENDS.keys()),
        }

        # Register default backends
        for name, config in DEFAULT_BACKENDS.items():
            container.register(name, config["class"])
            self._options[name] = dict(config["options"])

        # Set default backend
        self._default = "mongodb"

    @property
    def id(self) -> str:
        """Get registry ID."""
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get registry data."""
        return self._data

    async def init(self) -> None:
        """Initialize registry.

        This method initializes the default backend if one is set.
        """
        # Initialize default backend
        if self._default:
            await self.get(self._default)

    async def destroy(self) -> None:
        """Destroy registry.

        This method cleans up all registered backends.
        """
        # Cleanup all backends
        for name in list(self._options.keys()):
            await self.unregister(name)

    async def register(
        self, name: str, instance: Type[DatabaseBackend[Any]], **options: Any
    ) -> None:
        """Register database backend.

        Args:
            name: Backend name
            instance: Backend class
            **options: Backend options
                MongoDB options:
                    - uri: MongoDB connection URI
                    - database: Database name
                    - min_pool_size: Minimum pool size
                    - max_pool_size: Maximum pool size
                PostgreSQL options:
                    - host: Server hostname
                    - port: Server port
                    - database: Database name
                    - user: Username
                    - password: Password
                    - min_pool_size: Minimum pool size
                    - max_pool_size: Maximum pool size
                MySQL options:
                    - host: Server hostname
                    - port: Server port
                    - database: Database name
                    - user: Username
                    - password: Password
                    - min_pool_size: Minimum pool size
                    - max_pool_size: Maximum pool size

        Examples:
            ```python
            # MongoDB
            await registry.register(
                "mongodb",
                MongoBackend,
                uri="mongodb://localhost:27017",
                database="test"
            )

            # PostgreSQL
            await registry.register(
                "postgres",
                PostgresBackend,
                host="localhost",
                port=5432,
                database="test",
                user="postgres"
            )

            # MySQL
            await registry.register(
                "mysql",
                MySQLBackend,
                host="localhost",
                port=3306,
                database="test",
                user="root"
            )
            ```
        """
        # Register backend class
        container.register(name, instance)
        self._options[name] = options

        # Create and initialize instance
        backend = instance(**options)
        await backend.init()

    async def unregister(self, name: str) -> None:
        """Unregister database backend.

        Args:
            name: Backend name

        Examples:
            ```python
            await registry.unregister("mongodb")
            ```
        """
        if await self.has(name):
            # Get instance
            instance = await self.get(name)

            # Cleanup instance
            await instance.destroy()

            # Remove from registry
            del self._options[name]

            # Reset default if needed
            if self._default == name:
                self._default = None

    async def get(self, name: Optional[str] = None) -> DatabaseBackend[Any]:
        """Get database backend.

        Args:
            name: Backend name (optional)

        Returns:
            Database backend instance

        Raises:
            ValueError: If no backend specified and no default set

        Examples:
            ```python
            # Get default backend
            backend = await registry.get()

            # Get specific backend
            mongodb = await registry.get("mongodb")
            postgres = await registry.get("postgres")
            ```
        """
        if not name:
            name = await self.get_default()
        if not name:
            raise ValueError("No backend specified and no default set")

        # Get or create instance
        instance = await container.get(name)
        return cast(DatabaseBackend[Any], instance)

    async def switch(self, name: str, **options: Any) -> None:
        """Switch to different backend.

        This method:
        1. Destroys the current backend
        2. Updates options for the new backend
        3. Creates and initializes the new backend
        4. Sets it as the default

        Args:
            name: Backend name
            **options: Backend options (see register() for details)

        Examples:
            ```python
            # Switch to PostgreSQL
            await registry.switch(
                "postgres",
                host="localhost",
                port=5432,
                database="test"
            )

            # Switch to MySQL
            await registry.switch(
                "mysql",
                host="localhost",
                port=3306,
                database="test"
            )
            ```
        """
        if not await self.has(name):
            raise ValueError(f"Unknown backend: {name}")

        # Get current backend
        current_name = await self.get_default()
        if current_name:
            current = await self.get(current_name)
            await current.destroy()

        # Update options
        if name in self._options:
            self._options[name].update(options)
        else:
            self._options[name] = options

        # Set as default
        await self.set_default(name)

        # Initialize new backend
        backend = await self.get(name)
        await backend.init()

    def get_supported_backends(self) -> List[str]:
        """Get list of supported backend types.

        Returns:
            List of supported backend names

        Examples:
            ```python
            backends = registry.get_supported_backends()
            print(backends)  # ["mongodb", "postgres", "mysql"]
            ```
        """
        return list(DEFAULT_BACKENDS.keys())

    def get_backend_options(self, name: str) -> Dict[str, Any]:
        """Get default options for a backend type.

        Args:
            name: Backend name

        Returns:
            Default options for the backend

        Raises:
            ValueError: If backend type not supported

        Examples:
            ```python
            options = registry.get_backend_options("mongodb")
            print(options)  # {"uri": "mongodb://localhost:27017", ...}
            ```
        """
        if name not in DEFAULT_BACKENDS:
            raise ValueError(f"Unsupported backend type: {name}")
        return dict(DEFAULT_BACKENDS[name]["options"])
