"""System configuration model.

This module provides the SystemConfig model for storing system-wide configuration.

Examples:
    >>> from earnorm.di import container
    >>> config = container.get("config")
    >>> print(config.mongodb_uri)
    >>> config.redis_host = "localhost"
    >>> await config.write({"redis_host": "localhost"})
"""

import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Self, TypeVar, Union

import yaml
from dotenv import load_dotenv

from earnorm.base.env import Environment
from earnorm.base.model import BaseModel
from earnorm.config.data import SystemConfigData
from earnorm.exceptions import ConfigError, ConfigValidationError
from earnorm.fields import BaseField, DictField, StringField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.json import JSONField
from earnorm.fields.primitive.number import IntegerField

logger = logging.getLogger(__name__)

# Config prefixes
CONFIG_PREFIXES = ("MONGO_", "REDIS_", "CACHE_", "EVENT_")

# Type for config data
ConfigData = Dict[str, Union[str, int, bool]]

# Type variable for SystemConfig
T = TypeVar("T", bound="SystemConfig")


def validate_pool_sizes(min_size: Optional[int], max_size: Optional[int]) -> None:
    """Validate pool size configuration.

    Args:
        min_size: Minimum pool size
        max_size: Maximum pool size

    Raises:
        ConfigValidationError: If validation fails
    """
    if min_size is None or max_size is None:
        return

    if min_size > max_size:
        raise ConfigValidationError(
            f"Minimum pool size ({min_size}) cannot be greater than "
            f"maximum pool size ({max_size})"
        )


class SystemConfig(BaseModel):
    """System configuration model.

    This model represents system-wide configuration with validation rules.
    Config can be loaded from environment variables or YAML files.

    Examples:
        >>> # Load from .env file
        >>> config = await SystemConfig.load_env(".env")
        >>> print(config.database_uri)

        >>> # Load from YAML file
        >>> config = await SystemConfig.load_yaml("config.yaml")
        >>> print(config.redis_host)
    """

    _name = "earnorm.config"
    _description = "System Configuration"
    _skip_default_fields = True  # Skip default fields like created_at, updated_at

    # Singleton instance
    _instance: ClassVar[Optional["SystemConfig"]] = None

    @classmethod
    def __init_subclass__(cls) -> None:
        """Initialize subclass.

        This method ensures fields are properly initialized when subclassing SystemConfig.
        It copies all field definitions from the class to _fields for backward compatibility.
        """
        super().__init_subclass__()
        # Get all class attributes that are BaseField instances
        fields: Dict[str, BaseField[Any]] = {
            name: field
            for name, field in cls.__dict__.items()
            if isinstance(field, BaseField)
        }
        cls._fields = fields

    # Version and timestamps
    version = StringField(default="1.0.0")
    created_at = DateTimeField(auto_now_add=True, required=False)
    updated_at = DateTimeField(auto_now=True, required=False)

    # Database Configuration
    database_backend = StringField(
        default="mongodb",
        choices=["mongodb", "mysql", "postgres"],
        description="Database backend type",
    )
    database_uri = StringField(
        required=True,
        pattern=r"^(mongodb|mysql|postgres)://[^/\s]+(/[^/\s]*)?$",  # Validate URI format
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
    database_options = DictField(
        key_field=StringField(),
        value_field=JSONField(),
        required=False,
        default={
            "server_selection_timeout_ms": 5000,
            "connect_timeout_ms": 10000,
            "socket_timeout_ms": 20000,
            "retry_writes": True,
            "retry_reads": True,
            "w": 1,
            "j": True,
        },
        description="Additional database connection options",
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

    # Event Configuration
    event_enabled = BooleanField(
        default=True,
        description="Whether to enable event system",
    )
    event_queue = StringField(
        default="earnorm:events",
        min_length=1,
        max_length=255,
        description="Event queue name",
    )
    event_batch_size = IntegerField(
        default=100,
        min_value=1,
        max_value=10000,
        description="Event batch size",
    )

    @classmethod
    async def create_temp(
        cls, env: Environment, database_uri: str, database_name: str
    ) -> "SystemConfig":
        """Create a temporary SystemConfig instance with minimal required fields.

        This method is used to create a temporary SystemConfig instance for initializing
        the DI container. It only validates the required fields for database connection.

        Args:
            env: Environment instance
            database_uri: Database connection URI
            database_name: Database name

        Returns:
            Temporary SystemConfig instance

        Raises:
            ConfigValidationError: If validation fails
        """
        logger.debug("Creating temporary SystemConfig")
        logger.debug(f"Environment: {env}")
        logger.debug(f"Database URI: {database_uri}")
        logger.debug(f"Database name: {database_name}")

        try:
            # Create instance with env
            instance = cls._browse(env, [])

            # Create temporary config with minimal required fields
            await instance._create(
                {
                    "database_uri": str(database_uri),
                    "database_name": str(database_name),
                    "redis_host": "localhost",  # Default value for temporary config
                    "database_options": {
                        "server_selection_timeout_ms": 5000,
                        "connect_timeout_ms": 10000,
                        "socket_timeout_ms": 20000,
                        "retry_writes": True,
                        "retry_reads": True,
                        "w": 1,
                        "j": True,
                    },
                }
            )
            logger.debug("Successfully created temporary SystemConfig")
            return instance

        except Exception as e:
            logger.error(f"Failed to create temporary SystemConfig: {str(e)}")
            raise

    def validate(self) -> None:
        """Validate all configuration settings.

        This method runs all validation checks on the configuration:
        - Database configuration (URI, pool sizes, timeouts)
        - Redis configuration (host, port, pool sizes)
        - Cache configuration (backend type, TTL values)

        Raises:
            ConfigValidationError: If any validation check fails
        """
        self._validate_database_config()
        self._validate_redis_config()
        self._validate_cache_config()

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
            "max_lifetime": self.database_max_lifetime,
            "idle_timeout": self.database_idle_timeout,
            "ssl": self.database_ssl,
            "ssl_ca": self.database_ssl_ca,
            "ssl_cert": self.database_ssl_cert,
            "ssl_key": self.database_ssl_key,
        }

    @property
    def redis(self) -> Dict[str, Any]:
        """Get Redis configuration.

        Returns:
            Dictionary with Redis configuration
        """
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "min_pool_size": self.redis_min_pool_size,
            "max_pool_size": self.redis_max_pool_size,
            "pool_timeout": self.redis_pool_timeout,
        }

    @property
    def cache(self) -> Dict[str, Any]:
        """Get cache configuration.

        Returns:
            Dictionary with cache configuration
        """
        return {
            "backend": self.cache_backend,
            "ttl": self.cache_ttl,
        }

    def _validate_database_config(self) -> None:
        """Validate database configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        validate_pool_sizes(self.database_min_pool_size, self.database_max_pool_size)

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        validate_pool_sizes(self.redis_min_pool_size, self.redis_max_pool_size)

    def _validate_cache_config(self) -> None:
        """Validate cache configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        if self.cache_backend == "redis":
            self._validate_redis_config()

    @classmethod
    async def load_env(cls, env_file: Optional[Union[str, Path]] = None) -> Self:
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            SystemConfig instance

        Raises:
            ConfigError: If loading fails
        """
        try:
            # Load .env file if provided
            if env_file:
                load_dotenv(env_file)

            # Get all environment variables with config prefixes
            config_data: ConfigData = {}
            for key, value in os.environ.items():
                if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                    config_data[key.lower()] = value

            # Create config instance
            return await cls.create(values=config_data)

        except Exception as e:
            raise ConfigError(f"Failed to load config from environment: {e}") from e

    @classmethod
    async def load_yaml(cls, yaml_file: Union[str, Path]) -> Self:
        """Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            SystemConfig instance

        Raises:
            ConfigError: If loading fails
        """
        try:
            # Read YAML file
            with open(yaml_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Create config instance
            return await cls.create(values=config_data)

        except Exception as e:
            raise ConfigError(f"Failed to load config from YAML: {e}") from e

    @classmethod
    async def from_data(
        cls, env: Environment, data: SystemConfigData
    ) -> "SystemConfig":
        """Create a new SystemConfig instance from data.

        Args:
            env: Environment instance
            data: Configuration data to create from

        Returns:
            New SystemConfig instance
        """
        # Convert data to dict
        values = data.to_dict()

        # Create new instance with env
        instance = cls._browse(env, [])

        # Create record
        await instance._create(values)

        return instance
