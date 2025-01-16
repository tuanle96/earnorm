"""Config model module.

This module defines the SystemConfig model that represents system-wide configuration.
It follows the singleton pattern - only one instance exists in the database.

Examples:
    >>> config = await SystemConfig.get_instance()
    >>> print(config.mongo_uri)
    >>> config.redis_host = "localhost"
    >>> await config.save()
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, ClassVar, Dict, List, Optional, Union, cast

import yaml
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from earnorm import models
from earnorm.cache import cached
from earnorm.config.exceptions import (
    ConfigEncryptionError,
    ConfigError,
    ConfigValidationError,
)
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


class SystemConfig(models.BaseModel):
    """System configuration singleton model.

    This model represents system-wide configuration and follows
    the singleton pattern - only one instance exists in the database.
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

    # Encryption key
    _encryption_key: ClassVar[Optional[bytes]] = None

    # Change listeners
    _listeners: ClassVar[List[ConfigListener]] = []

    # Version and timestamps
    version = StringField(default="1.0.0")
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    # MongoDB Configuration
    mongo_uri = StringField(
        required=True, pattern=r"^mongodb://", description="MongoDB connection URI"
    )
    mongo_database = StringField(required=True, description="MongoDB database name")
    mongo_min_pool_size = IntegerField(
        default=5, min_value=1, description="Minimum MongoDB connection pool size"
    )
    mongo_max_pool_size = IntegerField(
        default=20, min_value=1, description="Maximum MongoDB connection pool size"
    )
    mongo_timeout = IntegerField(
        default=30, min_value=1, description="MongoDB connection timeout in seconds"
    )
    mongo_max_lifetime = IntegerField(
        default=3600, min_value=1, description="Maximum connection lifetime in seconds"
    )
    mongo_idle_timeout = IntegerField(
        default=300, min_value=1, description="Connection idle timeout in seconds"
    )

    # Redis Configuration
    redis_host = StringField(required=True, description="Redis server host")
    redis_port = IntegerField(
        default=6379, min_value=1, max_value=65535, description="Redis server port"
    )
    redis_db = IntegerField(default=0, min_value=0, description="Redis database number")
    redis_min_pool_size = IntegerField(
        default=5, min_value=1, description="Minimum Redis connection pool size"
    )
    redis_max_pool_size = IntegerField(
        default=20, min_value=1, description="Maximum Redis connection pool size"
    )
    redis_timeout = IntegerField(
        default=30, min_value=1, description="Redis connection timeout in seconds"
    )

    # Cache Configuration
    cache_enabled = BooleanField(default=True, description="Whether to enable caching")
    cache_ttl = IntegerField(
        default=3600, min_value=1, description="Default cache TTL in seconds"
    )
    cache_prefix = StringField(default="earnorm:", description="Cache key prefix")
    cache_max_retries = IntegerField(
        default=3, min_value=1, description="Maximum cache operation retries"
    )

    # Event Configuration
    event_enabled = BooleanField(
        default=True, description="Whether to enable event system"
    )
    event_queue = StringField(default="earnorm:events", description="Event queue name")
    event_batch_size = IntegerField(
        default=100, min_value=1, description="Event batch size"
    )

    def __init__(self, **data: Any) -> None:
        """Initialize config instance."""
        super().__init__(**data)
        self._validate_pool_sizes()

    def _validate_pool_sizes(self) -> None:
        """Validate pool size configurations."""
        # Validate MongoDB pool sizes
        validate_pool_sizes(
            self._data["mongo_min_pool_size"], self._data["mongo_max_pool_size"]
        )

        # Validate Redis pool sizes
        validate_pool_sizes(
            self._data["redis_min_pool_size"], self._data["redis_max_pool_size"]
        )

    @classmethod
    @cached(ttl=300)  # Cache for 5 minutes
    async def get_instance(cls) -> "SystemConfig":
        """Get singleton instance of config."""
        if cls._instance is None:
            instances = await cls.find({})
            if not instances:
                instance = cls()
                await instance.save()
                cls._instance = cast("SystemConfig", instance)
            else:
                cls._instance = cast("SystemConfig", instances[0])
        assert cls._instance is not None
        return cls._instance

    async def save(self) -> None:
        """Save config to database."""
        try:
            # Validate pool sizes
            self._validate_pool_sizes()

            # Update timestamp
            self.updated_at = datetime.now(timezone.utc)

            # Delete any existing configs
            await self.delete()

            # Save new config
            await super().save()

            # Update singleton instance
            self.__class__._instance = cast("SystemConfig", self)

            # Notify listeners
            await self.notify_listeners()

            # Log change
            logger.info(f"Config updated: {self.data}")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise ConfigError(f"Failed to save config: {e}")

    async def write(self, data: Dict[str, Any]) -> None:
        """Update config with new data and save to database.

        Args:
            data: Dictionary containing new config values

        Examples:
            >>> config = await SystemConfig.get_instance()
            >>> await config.write({
            ...     "redis_host": "localhost",
            ...     "redis_port": 6379
            ... })
        """
        try:
            # Update fields
            for key, value in data.items():
                if hasattr(self, key):
                    if key in self._sensitive_fields:
                        value = self.encrypt_value(str(value))
                    setattr(self, key, value)

            # Save to database
            await self.save()

        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            raise ConfigError(f"Failed to write config: {e}")

    @classmethod
    def set_encryption_key(cls, key: bytes) -> None:
        """Set encryption key for sensitive data.

        Args:
            key: Encryption key (must be 32 url-safe base64-encoded bytes)

        Examples:
            >>> key = Fernet.generate_key()
            >>> SystemConfig.set_encryption_key(key)
        """
        try:
            # Validate key
            Fernet(key)
            cls._encryption_key = key
            logger.info("Encryption key set successfully")
        except Exception as e:
            logger.error(f"Invalid encryption key: {e}")
            raise ConfigEncryptionError(f"Invalid encryption key: {e}")

    def encrypt_value(self, value: str) -> str:
        """Encrypt sensitive value.

        Args:
            value: Value to encrypt

        Returns:
            Encrypted value

        Raises:
            ConfigEncryptionError: If encryption fails
        """
        if not self._encryption_key:
            return value
        try:
            f = Fernet(self._encryption_key)
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt value: {e}")
            raise ConfigEncryptionError(f"Failed to encrypt value: {e}")

    def decrypt_value(self, value: str) -> str:
        """Decrypt sensitive value.

        Args:
            value: Value to decrypt

        Returns:
            Decrypted value

        Raises:
            ConfigEncryptionError: If decryption fails
        """
        if not self._encryption_key:
            return value
        try:
            f = Fernet(self._encryption_key)
            return f.decrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            raise ConfigEncryptionError(f"Failed to decrypt value: {e}")

    async def migrate(self) -> None:
        """Migrate config to latest version.

        This method handles version upgrades by performing
        necessary migrations.

        Examples:
            >>> config = await SystemConfig.get_instance()
            >>> await config.migrate()
        """
        try:
            current_version = self._data["version"]
            if current_version == "1.0.0":
                # Add new fields with defaults
                self.cache_max_retries = 3
                self.event_batch_size = 100
                self.version = "1.1.0"
                await self.save()
                logger.info(f"Migrated config from {current_version} to 1.1.0")

        except Exception as e:
            logger.error(f"Failed to migrate config: {e}")
            raise ConfigError(f"Failed to migrate config: {e}")

    async def backup(self, path: str) -> None:
        """Backup config to file.

        Args:
            path: Path to backup file

        Examples:
            >>> config = await SystemConfig.get_instance()
            >>> await config.backup("config_backup.yaml")
        """
        try:
            data = self.data

            # Remove internal fields
            data.pop("_id", None)

            with open(path, "w") as f:
                yaml.dump(data, f)

            logger.info(f"Config backed up to {path}")

        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            raise ConfigError(f"Failed to backup config: {e}")

    @classmethod
    async def restore(cls, path: str) -> "SystemConfig":
        """Restore config from backup file.

        Args:
            path: Path to backup file

        Returns:
            Restored config instance

        Examples:
            >>> config = await SystemConfig.restore("config_backup.yaml")
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            instance = await cls.get_instance()
            await instance.write(data)

            logger.info(f"Config restored from {path}")
            return instance

        except Exception as e:
            logger.error(f"Failed to restore config: {e}")
            raise ConfigError(f"Failed to restore config: {e}")

    @classmethod
    def add_listener(cls, listener: ConfigListener) -> None:
        """Add config change listener.

        Args:
            listener: Callback function to be called on config changes

        Examples:
            >>> async def on_config_change(config):
            ...     print(f"Config changed: {config.data}")
            >>> SystemConfig.add_listener(on_config_change)
        """
        cls._listeners.append(listener)
        logger.info(f"Added config change listener: {listener.__name__}")

    async def notify_listeners(self) -> None:
        """Notify listeners of config changes.

        This method is called automatically after each save.
        """
        for listener in self._listeners:
            try:
                await listener(self)
            except Exception as e:
                logger.error(f"Failed to notify listener {listener.__name__}: {e}")

    # List of fields containing sensitive data
    _sensitive_fields = {"mongo_uri", "redis_host"}

    @classmethod
    async def load_yaml(cls, yaml_path: Union[str, Path]) -> "SystemConfig":
        """Load config from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Config instance with loaded values

        Examples:
            >>> config = await SystemConfig.load_yaml("config.yaml")
            >>> print(config.mongo_uri)

        Raises:
            ConfigError: If file doesn't exist or is invalid
        """
        try:
            path = Path(yaml_path)
            if not path.exists():
                raise ConfigError(f"Config file not found: {path}")

            # Load YAML file
            with open(path) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ConfigError("YAML file must contain a dictionary")

            # Get or create instance
            instance = await cls.get_instance()
            await instance.write(cast(ConfigData, data))

            logger.info(f"Config loaded from YAML file: {path}")
            return instance

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML file: {e}")
            raise ConfigError(f"Invalid YAML file: {e}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise ConfigError(f"Failed to load config: {e}")

    @classmethod
    async def load_env(cls, env_path: Union[str, Path]) -> "SystemConfig":
        """Load config from ENV file.

        Args:
            env_path: Path to ENV file

        Returns:
            Config instance with loaded values

        Examples:
            >>> config = await SystemConfig.load_env(".env")
            >>> print(config.mongo_uri)

        Raises:
            ConfigError: If file doesn't exist or is invalid
        """
        try:
            path = Path(env_path)
            if not path.exists():
                raise ConfigError(f"Config file not found: {path}")

            # Load .env file
            load_dotenv(str(path))

            # Convert env vars to dict
            data: ConfigData = {}
            for key, value in os.environ.items():
                # Only include our env vars
                if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                    # Convert key to lowercase for model fields
                    field_key = key.lower()
                    data[field_key] = value

            # Get or create instance
            instance = await cls.get_instance()
            await instance.write(data)

            logger.info(f"Config loaded from ENV file: {path}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise ConfigError(f"Failed to load config: {e}")

    @classmethod
    async def load_config(cls, config_path: Union[str, Path]) -> "SystemConfig":
        """Load config from file.

        This method detects the file type based on extension and calls
        the appropriate loader.

        Args:
            config_path: Path to config file

        Returns:
            Config instance with loaded values

        Examples:
            >>> config = await SystemConfig.load_config("config.yaml")
            >>> config = await SystemConfig.load_config(".env")

        Raises:
            ConfigError: If file format is not supported
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")

        # Get file extension
        ext = path.suffix.lower()

        # Load based on extension
        if ext in (".yaml", ".yml"):
            return await cls.load_yaml(path)
        elif ext == ".env":
            return await cls.load_env(path)
        else:
            raise ConfigError(f"Unsupported config format: {ext}")
