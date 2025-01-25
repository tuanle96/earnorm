"""Environment module for managing database connections and caching.

This module provides the Environment class which manages:
1. Database connections and transactions through Database Adapters
2. Model registration
3. Record caching and prefetching
4. Configuration management

Examples:
    >>> env = Environment(config)
    >>> await env.init()
    >>> adapter = await env.get_adapter()
    >>> await env.destroy()
"""

from typing import Any, Dict, Optional, Set, Type, TypeVar, Union, cast

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.cache.core.manager import CacheManager
from earnorm.config.model import SystemConfig
from earnorm.di import container
from earnorm.types import DatabaseModel

# Type aliases
CacheKey = str
CacheValue = Union[str, int, float, bool, Dict[str, Any], None]
T = TypeVar("T")

ModelT = TypeVar("ModelT", bound=DatabaseModel)

# Available database adapters - will be populated by specific backends
ADAPTERS: Dict[str, Type[DatabaseAdapter[DatabaseModel]]] = {}


class Environment:
    """Environment class for managing database connections and caching.

    Attributes:
        config: System configuration
        _models: Dictionary mapping model names to model classes
        _cache_manager: Cache manager for caching records
        _prefetch: Dictionary mapping model names to prefetch record IDs
        _adapter: Database adapter instance
        _backend_type: Database backend type
    """

    def __init__(self, config: SystemConfig) -> None:
        """Initialize environment."""
        self.config = config
        self._models: Dict[str, Type[DatabaseModel]] = {}
        self._cache_manager: Optional[CacheManager] = None
        self._prefetch: Dict[str, Set[int]] = {}
        self._backend_type: str = config.database.get("backend_type", "")  # type: ignore
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None

    async def init(self) -> None:
        """Initialize environment.

        This method:
        1. Gets cache manager from container
        2. Initializes database adapter
        """
        # Get cache manager
        self._cache_manager = await container.get("cache_manager")

        # Initialize database adapter
        adapter_class = ADAPTERS.get(self._backend_type)
        if not adapter_class:
            raise ValueError(f"Unsupported database backend: {self._backend_type}")

        self._adapter = adapter_class()
        await self._adapter.init()

    async def destroy(self) -> None:
        """Destroy environment.

        This method:
        1. Closes database adapter if exists
        2. Cleans up resources
        """
        if self._adapter:
            await self._adapter.close()
            self._adapter = None

        self._cache_manager = None
        self._models.clear()
        self._prefetch.clear()

    async def get_adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter instance."""
        if not self._adapter:
            raise RuntimeError("Database adapter not initialized")
        return self._adapter

    async def get_connection(self) -> Any:
        """Get database connection.

        Returns:
            Database connection from adapter

        Raises:
            RuntimeError: If adapter not initialized
        """
        adapter = await self.get_adapter()
        return await adapter.get_connection()

    @property
    def backend_type(self) -> str:
        """Get database backend type.

        Returns:
            Database backend type (e.g. "mongodb", "mysql", "postgres")
        """
        return self._backend_type

    async def register_model(self, name: str, model: Type[DatabaseModel]) -> None:
        """Register model.

        Args:
            name: Model name
            model: Model class

        Raises:
            ValueError: If model already registered
        """
        if name in self._models:
            raise ValueError(f"Model {name} already registered")
        self._models[name] = model

    async def unregister_model(self, name: str) -> None:
        """Unregister model.

        Args:
            name: Model name
        """
        if name in self._models:
            del self._models[name]

    def get_model(self, name: str) -> Type[DatabaseModel]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class

        Raises:
            KeyError: If model not found
        """
        if name not in self._models:
            raise KeyError(f"Model {name} not found")
        return self._models[name]

    async def get_cached(self, model: str, record_id: int) -> Optional[Dict[str, Any]]:
        """Get cached record.

        Args:
            model: Model name
            record_id: Record ID

        Returns:
            Cached record data or None if not found
        """
        if not self._cache_manager:
            return None

        key = f"{model}:{record_id}"
        try:
            value = await self._cache_manager.get(key)
            if value is None:
                return None
            return cast(Dict[str, Any], value)
        except (AttributeError, NotImplementedError):
            return None

    async def set_cached(
        self,
        model: str,
        record_id: int,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Cache record data.

        Args:
            model: Model name
            record_id: Record ID
            data: Record data to cache
            ttl: Cache TTL in seconds
        """
        if not self._cache_manager:
            return

        key = f"{model}:{record_id}"
        try:
            await self._cache_manager.set(key, data, ttl=ttl)
        except (AttributeError, NotImplementedError):
            return

    async def clear_caches(self) -> None:
        """Clear all caches."""
        if self._cache_manager:
            # Get all keys from models
            keys = [f"{model}:*" for model in self._models.keys()]
            await self._cache_manager.delete_many(keys)

    def clear_prefetch(self) -> None:
        """Clear prefetch data."""
        self._prefetch.clear()

    async def prefetch_records(self, model: str, ids: Set[int]) -> None:
        """Prefetch records.

        Args:
            model: Model name
            ids: Record IDs to prefetch
        """
        if model not in self._prefetch:
            self._prefetch[model] = set()
        self._prefetch[model].update(ids)

    def get_prefetch(self, model: str) -> Set[int]:
        """Get prefetched record IDs.

        Args:
            model: Model name

        Returns:
            Set of prefetched record IDs
        """
        return self._prefetch.get(model, set())
