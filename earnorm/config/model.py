"""Config model module.

This module defines the SystemConfig model that represents system-wide configuration.
It follows the singleton pattern - only one instance exists in the database.

Examples:
    >>> from earnorm.di import container
    >>> config = container.get("config")
    >>> print(config.mongodb_uri)
    >>> config.redis_host = "localhost"
    >>> await config.save()
"""

import logging
import os
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

import yaml
from dotenv import load_dotenv

from earnorm.base import BaseModel
from earnorm.cache import cached
from earnorm.di import container
from earnorm.exceptions import ConfigError, ConfigValidationError
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.string import StringField

logger = logging.getLogger(__name__)

# Type for config change listener
ConfigListener = Callable[["SystemConfig"], Awaitable[None]]

# Config prefixes
CONFIG_PREFIXES = ("MONGO_", "REDIS_", "CACHE_", "EVENT_")

# Type for config data
ConfigData = Dict[str, Union[str, int, bool]]

# Type variable for SystemConfig
T = TypeVar("T", bound="SystemConfig")


def validate_pool_sizes(min_size: int, max_size: int) -> None:
    """Validate pool size configuration.

    Args:
        min_size: Minimum pool size
        max_size: Maximum pool size

    Raises:
        ConfigValidationError: If validation fails
    """
    if min_size > max_size:
        raise ConfigValidationError(
            f"Minimum pool size ({min_size}) cannot be greater than "
            f"maximum pool size ({max_size})"
        )


class SystemConfig(BaseModel):
    """System configuration singleton model.

    This model represents system-wide configuration and follows
    the singleton pattern - only one instance exists in the database.

    The config is automatically loaded into the DI container on startup
    and can be accessed through the environment in BaseModel:

    Examples:
        ```python
        class MyModel(BaseModel):
            def my_method(self):
                config = self.env.config
                mongo_uri = config.mongodb_uri
        ```
    """

    # Collection configuration
    _collection = "system_config"
    _name = "system_config"

    # Collection indexes
    indexes = [
        {"keys": [("version", 1)]},
        {"keys": [("created_at", -1)]},
        {"keys": [("updated_at", -1)]},
    ]

    # Singleton instance
    _instance: ClassVar[Optional["SystemConfig"]] = None

    # Change listeners
    _listeners: ClassVar[List[ConfigListener]] = []

    # Version and timestamps
    version = StringField(default="1.0.0")
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    # Database Configuration
    database_backend = StringField(
        default="mongodb",
        choices=["mongodb", "mysql", "postgres"],
        description="Database backend type",
    )
    database_uri = StringField(
        required=True,
        min_length=10,
        description="Database connection URI",
    )
    database_name = StringField(
        required=True,
        min_length=1,
        max_length=64,
        description="Database name",
    )
    database_username = StringField(
        required=False,
        description="Database username",
    )
    database_password = StringField(
        required=False,
        description="Database password",
    )
    database_min_pool_size = IntegerField(
        default=5,
        min_value=1,
        max_value=100,
        description="Minimum database connection pool size",
    )
    database_max_pool_size = IntegerField(
        default=20,
        min_value=5,
        max_value=1000,
        description="Maximum database connection pool size",
    )
    database_pool_timeout = IntegerField(
        default=30,
        min_value=1,
        max_value=300,
        description="Database connection timeout in seconds",
    )
    database_max_lifetime = IntegerField(
        default=3600,
        min_value=60,
        max_value=86400,  # 24 hours
        description="Maximum connection lifetime in seconds",
    )
    database_idle_timeout = IntegerField(
        default=300,
        min_value=10,
        max_value=3600,
        description="Connection idle timeout in seconds",
    )
    database_ssl = BooleanField(
        default=False,
        description="Whether to use SSL for database connection",
    )
    database_ssl_ca = StringField(
        required=False,
        description="SSL CA certificate path",
    )
    database_ssl_cert = StringField(
        required=False,
        description="SSL certificate path",
    )
    database_ssl_key = StringField(
        required=False,
        description="SSL key path",
    )

    # Redis Configuration
    redis_host = StringField(
        required=True, min_length=1, max_length=255, description="Redis server host"
    )
    redis_port = IntegerField(
        default=6379, min_value=1, max_value=65535, description="Redis server port"
    )
    redis_db = IntegerField(
        default=0, min_value=0, max_value=15, description="Redis database number"
    )
    redis_min_pool_size = IntegerField(
        default=5,
        min_value=1,
        max_value=100,
        description="Minimum Redis connection pool size",
    )
    redis_max_pool_size = IntegerField(
        default=20,
        min_value=5,
        max_value=1000,
        description="Maximum Redis connection pool size",
    )
    redis_pool_timeout = IntegerField(
        default=30,
        min_value=1,
        max_value=300,
        description="Redis connection timeout in seconds",
    )

    # Cache Configuration
    cache_backend = StringField(
        default="redis", choices=["redis", "memory"], description="Cache backend type"
    )
    cache_ttl = IntegerField(
        default=3600,
        min_value=1,
        max_value=86400,  # 24 hours
        description="Default cache TTL in seconds",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize config instance."""
        super().__init__(**data)
        # Run all validations
        self._validate_all()

    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration.

        Returns:
            Dictionary with database configuration
        """
        return {
            "backend_type": self.database_backend,
            "uri": self.database_uri,
            "database": self.database_name,
            "username": self.database_username,
            "password": self.database_password,
            "pool_size": self.database_max_pool_size,
            "pool_timeout": self.database_pool_timeout,
            "pool_recycle": self.database_max_lifetime,
            "ssl": self.database_ssl,
            "ssl_ca": self.database_ssl_ca,
            "ssl_cert": self.database_ssl_cert,
            "ssl_key": self.database_ssl_key,
        }

    @classmethod
    @cached(ttl=300)
    async def get_instance(cls: Type[T]) -> T:
        """Get singleton instance of config."""
        if cls._get_instance() is None:
            instances = await cls.search([])

            if not instances:
                instance = cls()
                await instance.save()
                cls._set_instance(instance)
            else:
                cls._set_instance(instances)

                if len(instances) > 1:
                    for other in instances[1:]:
                        await other.unlink()

        assert cls._get_instance() is not None
        return cast(T, cls._get_instance())

    def _validate_all(self) -> None:
        """Run all validation checks."""
        self._validate_database_config()
        self._validate_redis_config()
        self._validate_cache_config()

    def _validate_database_config(self) -> None:
        """Validate database configuration.

        Validates:
        - URI format and required components
        - Database name format
        - Pool sizes and relationships
        - Timeout values and relationships
        """
        # Validate database name
        db_name = str(self.database_name)
        if not db_name.isalnum():
            raise ConfigValidationError(
                f"Invalid database name: {db_name}. Must be alphanumeric"
            )

        # Validate pool sizes
        min_size = self.database_min_pool_size
        max_size = self.database_max_pool_size
        if min_size is not None and max_size is not None and min_size > max_size:
            raise ConfigValidationError(
                f"Minimum database pool size ({min_size}) cannot be greater than "
                f"maximum pool size ({max_size})"
            )

        # Validate timeouts
        pool_timeout = self.database_pool_timeout
        idle_timeout = self.database_idle_timeout
        max_lifetime = self.database_max_lifetime

        if (
            pool_timeout is not None
            and idle_timeout is not None
            and pool_timeout >= idle_timeout
        ):
            raise ConfigValidationError(
                f"Pool timeout ({pool_timeout}s) must be less than "
                f"idle timeout ({idle_timeout}s)"
            )

        if (
            idle_timeout is not None
            and max_lifetime is not None
            and idle_timeout >= max_lifetime
        ):
            raise ConfigValidationError(
                f"Idle timeout ({idle_timeout}s) must be less than "
                f"max lifetime ({max_lifetime}s)"
            )

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration.

        Validates:
        - Host format
        - Port range
        - Database number range
        - Pool sizes and relationships
        - Timeout values
        """
        # Validate host format
        host = str(self.redis_host)
        if not host:
            raise ConfigValidationError("Redis host cannot be empty")

        # Validate port range
        port = self.redis_port
        if port is not None and not 1 <= port <= 65535:
            raise ConfigValidationError(
                f"Invalid Redis port: {port}. Must be between 1 and 65535"
            )

        # Validate database number
        db = self.redis_db
        if db is not None and not 0 <= db <= 15:
            raise ConfigValidationError(
                f"Invalid Redis database number: {db}. Must be between 0 and 15"
            )

        # Validate pool sizes
        min_size = self.redis_min_pool_size
        max_size = self.redis_max_pool_size
        if min_size is not None and max_size is not None:
            validate_pool_sizes(min_size, max_size)

        # Validate timeout
        timeout = self.redis_pool_timeout
        if timeout is not None and timeout < 1:
            raise ConfigValidationError(
                f"Invalid Redis connection timeout: {timeout}. Must be greater than 0"
            )

    def _validate_cache_config(self) -> None:
        """Validate cache configuration.

        Validates:
        - Backend type is supported
        - TTL values are reasonable
        """
        # Validate cache backend
        backend = str(self.cache_backend)
        if backend not in ["redis", "memory"]:
            raise ConfigValidationError(
                f"Invalid cache backend: {backend}. Must be one of: redis, memory"
            )

        # Validate TTL
        ttl = self.cache_ttl
        if ttl is not None and ttl <= 0:
            raise ConfigValidationError(
                f"Invalid cache TTL: {ttl}. Must be greater than 0"
            )

        if ttl is not None and ttl > 86400:  # 24 hours
            raise ConfigValidationError(
                f"Invalid cache TTL: {ttl}. Must not exceed 24 hours (86400 seconds)"
            )

    @classmethod
    def add_listener(cls, listener: ConfigListener) -> None:
        """Add config change listener.

        Args:
            listener: Async function to call when config changes
        """
        cls._listeners.append(listener)

    async def notify_listeners(self) -> None:
        """Notify all listeners of config change."""
        for listener in self._listeners:
            try:
                await listener(self)
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error("Failed to notify listener: %s", str(e))

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Create config instance from environment variables.

        Returns:
            SystemConfig instance with values from environment

        Examples:
            >>> config = SystemConfig.from_env()
            >>> print(config.mongodb_uri)
        """
        # Load .env file if exists
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)

        # Get all environment variables with config prefixes
        data: Dict[str, Any] = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                field_name = key.lower()
                if field_name in cls._fields:
                    data[field_name] = value

        return cls(**data)

    @classmethod
    def from_yaml(cls, path: str) -> "SystemConfig":
        """Create config instance from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            SystemConfig instance with values from YAML

        Examples:
            >>> config = SystemConfig.from_yaml("config.yaml")
            >>> print(config.mongodb_uri)
        """
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    async def to_yaml(self, path: str) -> None:
        """Save config to YAML file.

        Args:
            path: Path to save YAML file

        Examples:
            >>> config = await SystemConfig.get_instance()
            >>> await config.to_yaml("config.yaml")
        """
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f)

    @classmethod
    async def load(cls) -> None:
        """Load config into DI container.

        This method is called on startup to load the config
        into the DI container for access through the environment.

        Examples:
            ```python
            # In your application startup
            await SystemConfig.load()

            # Then in your models
            class MyModel(BaseModel):
                def my_method(self):
                    config = self.env.config
                    uri = config.mongodb_uri
            ```
        """
        try:
            instance = await cls.get_instance()
            container.register("config", instance)
            logger.info("System config loaded successfully")
        except Exception as e:
            logger.error("Failed to load system config: %s", str(e))
            raise ConfigError(f"Failed to load system config: {e}") from e

    @classmethod
    def _set_instance(cls, instance: Optional["SystemConfig"]) -> None:
        """Set singleton instance."""
        cls._instance = instance

    @classmethod
    def _get_instance(cls) -> Optional["SystemConfig"]:
        """Get singleton instance."""
        return cls._instance

    async def reload(self) -> None:
        """Reload config from database."""
        try:

            # Reload from database
            instance = await self.__class__.get_instance()

            # Update container
            container.register("config", instance)

            logger.info("System config reloaded successfully")
        except Exception as e:
            logger.error("Failed to reload system config: %s", str(e))
            raise ConfigError(f"Failed to reload system config: {e}") from e

    async def apply(self) -> None:
        """Apply config changes to system."""
        try:
            # Save changes
            await self.save()

            # Get all services that depend on config
            database = await container.get("database_registry")
            cache = await container.get("cache_manager")

            # Update services
            if hasattr(database, "reconnect"):
                await database.reconnect()
            if hasattr(cache, "reconfigure"):
                await cache.reconfigure()

            logger.info("System config applied successfully")
        except Exception as e:
            logger.error("Failed to apply system config: %s", str(e))
            raise ConfigError(f"Failed to apply system config: {e}") from e
