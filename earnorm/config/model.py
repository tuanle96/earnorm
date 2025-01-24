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
from typing import Any, Awaitable, Callable, ClassVar, Dict, List, Optional, Type, TypeVar, Union, cast

import yaml
from dotenv import load_dotenv

from earnorm.base import BaseModel
from earnorm.cache import cached
from earnorm.config.exceptions import ConfigError, ConfigValidationError
from earnorm.di import container
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
    version: StringField = StringField(default="1.0.0")
    created_at: DateTimeField = DateTimeField(auto_now_add=True)
    updated_at: DateTimeField = DateTimeField(auto_now=True)

    # MongoDB Configuration
    mongodb_uri: StringField = StringField(
        required=True,
        pattern=r"^mongodb://",
        min_length=10,
        description="MongoDB connection URI",
    )
    mongodb_database: StringField = StringField(
        required=True, min_length=1, max_length=64, description="MongoDB database name"
    )
    mongodb_min_pool_size: IntegerField = IntegerField(
        default=5,
        min_value=1,
        max_value=100,
        description="Minimum MongoDB connection pool size",
    )
    mongodb_max_pool_size: IntegerField = IntegerField(
        default=20,
        min_value=5,
        max_value=1000,
        description="Maximum MongoDB connection pool size",
    )
    mongodb_pool_timeout: IntegerField = IntegerField(
        default=30,
        min_value=1,
        max_value=300,
        description="MongoDB connection timeout in seconds",
    )
    mongodb_max_lifetime: IntegerField = IntegerField(
        default=3600,
        min_value=60,
        max_value=86400,  # 24 hours
        description="Maximum connection lifetime in seconds",
    )
    mongodb_idle_timeout: IntegerField = IntegerField(
        default=300,
        min_value=10,
        max_value=3600,
        description="Connection idle timeout in seconds",
    )
    mongodb_validate_on_borrow: BooleanField = BooleanField(
        default=True, description="Whether to validate connections on borrow"
    )
    mongodb_test_on_return: BooleanField = BooleanField(
        default=True, description="Whether to test connections on return"
    )

    # Redis Configuration
    redis_host: StringField = StringField(
        required=True, min_length=1, max_length=255, description="Redis server host"
    )
    redis_port: IntegerField = IntegerField(
        default=6379, min_value=1, max_value=65535, description="Redis server port"
    )
    redis_db: IntegerField = IntegerField(
        default=0, min_value=0, max_value=15, description="Redis database number"
    )

    # Cache Configuration
    cache_backend: StringField = StringField(
        default="redis", choices=["redis", "memory"], description="Cache backend type"
    )
    cache_ttl: IntegerField = IntegerField(
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

    @classmethod
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_instance(cls: Type[T]) -> T:
        """Get singleton instance of config.

        This method ensures only one config instance exists in the database.
        If no config exists, it creates a default one.

        Returns:
            SystemConfig: The singleton config instance

        Examples:
            ```python
            config = await SystemConfig.get_instance()
            print(config.mongodb_uri)
            ```
        """
        if cls._instance is None:
            # Find existing config
            instances = await cls.search([])

            if not instances:
                # Create default config if none exists
                instance = cls()
                await instance.save()
                cls._instance = cast("SystemConfig", instance)
            else:
                # Use first (and should be only) config
                cls._instance = cast("SystemConfig", instances)

                # Delete any other configs to maintain singleton
                if len(instances) > 1:
                    for other in instances[1:]:
                        await other.unlink()

        assert cls._instance is not None
        return cast(T, cls._instance)

    async def save(self) -> None:
        """Save config to database.

        This method validates the config before saving and ensures
        only one config instance exists in the database.
        """
        try:

            # Update timestamp
            self.updated_at = DateTimeField(auto_now=True)

            # Save using BaseModel's save method
            await self.save()

            # Update singleton instance
            self.__class__._instance = cast("SystemConfig", self)

            # Update container
            container.register("config", self)

            # Log change
            logger.info(f"Config updated: {self.data}")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise ConfigError(f"Failed to save config: {e}")

    def _validate_all(self) -> None:
        """Run all validation checks."""
        self._validate_mongodb_config()
        self._validate_redis_config()
        self._validate_cache_config()

    def _validate_mongodb_config(self) -> None:
        """Validate MongoDB configuration.

        Validates:
        - URI format and required components
        - Database name format
        - Pool sizes and relationships
        - Timeout values and relationships
        """
        # Validate MongoDB URI format
        uri = str(self.mongodb_uri)
        if not uri.startswith("mongodb://"):
            raise ConfigValidationError(
                f"Invalid MongoDB URI format: {uri}. Must start with 'mongodb://'"
            )

        # Validate database name
        db_name = str(self.mongodb_database)
        if not db_name.isalnum():
            raise ConfigValidationError(
                f"Invalid MongoDB database name: {db_name}. Must be alphanumeric"
            )

        # Validate pool sizes
        min_size = int(self.mongodb_min_pool_size)
        max_size = int(self.mongodb_max_pool_size)
        if min_size > max_size:
            raise ConfigValidationError(
                f"Minimum MongoDB pool size ({min_size}) cannot be greater than "
                f"maximum pool size ({max_size})"
            )

        # Validate timeouts
        pool_timeout = int(self.mongodb_pool_timeout)
        idle_timeout = int(self.mongodb_idle_timeout)
        max_lifetime = int(self.mongodb_max_lifetime)

        if pool_timeout >= idle_timeout:
            raise ConfigValidationError(
                f"Pool timeout ({pool_timeout}s) must be less than "
                f"idle timeout ({idle_timeout}s)"
            )

        if idle_timeout >= max_lifetime:
            raise ConfigValidationError(
                f"Idle timeout ({idle_timeout}s) must be less than "
                f"max lifetime ({max_lifetime}s)"
            )

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration.

        Validates:
        - Host format and accessibility
        - Port range and availability
        - Database number range
        """
        # Validate Redis host
        host = str(self.redis_host)
        if not host:
            raise ConfigValidationError("Redis host cannot be empty")

        # Validate port range
        port = self.redis_port
        if not (1 <= int(port) <= 65535):
            raise ConfigValidationError(
                f"Invalid Redis port: {port}. Must be between 1 and 65535"
            )

        # Validate database number
        db = self.redis_db
        if not (0 <= db <= 15):
            raise ConfigValidationError(
                f"Invalid Redis database number: {db}. Must be between 0 and 15"
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
        ttl = int(self.cache_ttl)
        if ttl <= 0:
            raise ConfigValidationError(
                f"Invalid cache TTL: {ttl}. Must be greater than 0"
            )

        if ttl > 86400:  # 24 hours
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
            except Exception as e:
                logger.error(f"Failed to notify listener: {e}")

    @property
    def data(self) -> Dict[str, Any]:
        """Get config data as dictionary."""
        return {
            key: getattr(self, key).value
            for key in self._fields.keys()
            if not key.startswith("_") and hasattr(self, key)
        }

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
        with open(path) as f:
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
        with open(path, "w") as f:
            yaml.dump(self.data, f)

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
            logger.error(f"Failed to load system config: {e}")
            raise ConfigError(f"Failed to load system config: {e}")

    async def reload(self) -> None:
        """Reload config from database.

        This method reloads the config from database and updates
        the DI container. Useful when config has been updated by
        another process.

        Examples:
            ```python
            config = container.get("config")
            await config.reload()
            ```
        """
        try:
            # Clear instance cache
            self.__class__._instance = None

            # Reload from database
            instance = await self.__class__.get_instance()

            # Update container
            container.register("config", instance)

            logger.info("System config reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload system config: {e}")
            raise ConfigError(f"Failed to reload system config: {e}")

    async def apply(self) -> None:
        """Apply config changes to system.

        This method applies the current config values to the system.
        It updates all dependent services with the new configuration.

        Examples:
            ```python
            config = container.get("config")
            config.mongodb_uri = "mongodb://new-host:27017"
            await config.apply()
            ```
        """
        try:
            # Save changes
            await self.save()

            # Get all services that depend on config
            database = container.get("database_registry")
            cache = container.get("cache_manager")

            # Update services
            await database.reconnect()
            await cache.reconfigure()

            logger.info("System config applied successfully")
        except Exception as e:
            logger.error(f"Failed to apply system config: {e}")
            raise ConfigError(f"Failed to apply system config: {e}")
