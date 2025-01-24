"""Environment module for managing database connections and caching.

This module provides the Environment class which manages:
1. Database connections and transactions
2. Model registration and lifecycle
3. Record caching and prefetching
4. Configuration management

Examples:
    >>> env = Environment(config)
    >>> await env.init()
    >>> cached_data = await env.get_cached("user", 123)
    >>> await env.set_cached("user", 123, {"name": "John"})
    >>> await env.destroy()
"""

from typing import Any, Dict, Optional, Set, Type, TypeVar, Union, cast

from earnorm.base.model import BaseModel
from earnorm.cache.core.manager import CacheManager
from earnorm.config.model import SystemConfig
from earnorm.di import container
from earnorm.registry import Registry
from earnorm.registry.database import DatabaseRegistry
from earnorm.registry.model import ModelLifecycle

# Type aliases
CacheKey = str
CacheValue = Union[str, int, float, bool, Dict[str, Any], None]
ModelType = TypeVar("ModelType", bound=BaseModel)


class EnvironmentManager:
    """Environment manager for context management.

    This class manages environment context and database connections.
    It provides async context management for environment operations.

    Examples:
        >>> async with env.manage() as env:
        ...     # Operations in transaction
        ...     users = await env["res.users"].search([])
        ...     await users.write({"active": False})
        ...     # Transaction committed if no errors
    """

    def __init__(self, env: "Environment") -> None:
        """Initialize environment manager.

        Args:
            env: Environment instance
        """
        self.env = env
        self._db_registry: Optional[DatabaseRegistry] = None
        self._cache_enabled: bool = True

    async def __aenter__(self) -> "Environment":
        """Enter environment context.

        This method:
        1. Gets database registry
        2. Returns environment instance

        Returns:
            Environment instance
        """
        self._db_registry = await container.get("database_registry")
        if not self._db_registry:
            raise RuntimeError("Database registry not initialized")
        return self.env

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit environment context.

        This method:
        1. Cleans up resources (cache, prefetch)

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_type is not None:
            # Clear cache on error to avoid stale data
            await self.env.clear_caches()
        self.env.clear_prefetch()
        self._db_registry = None

    def disable_cache(self) -> None:
        """Disable caching for this context."""
        self._cache_enabled = False

    def enable_cache(self) -> None:
        """Enable caching for this context."""
        self._cache_enabled = True

    @property
    def cache_enabled(self) -> bool:
        """Check if caching is enabled.

        Returns:
            True if caching is enabled, False otherwise
        """
        return self._cache_enabled


class Environment:
    """Environment class for managing database connections and caching.

    Attributes:
        config: System configuration
        registry: Model registry
        _models: Dictionary mapping model names to model classes
        _cache_manager: Cache manager for caching records
        _prefetch: Dictionary mapping model names to prefetch record IDs
    """

    def __init__(self, config: SystemConfig) -> None:
        """Initialize environment.

        Args:
            config: System configuration
        """
        self.config = config
        self._registry: Optional[Registry[ModelLifecycle]] = None
        self._models: Dict[str, Type[BaseModel]] = {}
        self._cache_manager: Optional[CacheManager] = None
        self._prefetch: Dict[str, Set[int]] = {}

    async def init(self) -> None:
        """Initialize environment.

        This method:
        1. Gets registry from container
        2. Initializes registry with configuration
        3. Gets cache manager from container
        """
        # Init registry
        self._registry = await container.get("registry")
        if self._registry:
            await self._registry.init()

        # Get cache manager
        self._cache_manager = await container.get("cache_manager")

    async def destroy(self) -> None:
        """Destroy environment.

        This method:
        1. Destroys registry if exists
        2. Cleans up resources
        """
        if self._registry:
            await self._registry.destroy()
            self._registry = None

        self._cache_manager = None
        self._models.clear()
        self._prefetch.clear()

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
        if self._registry:
            await self._registry.clear_caches()

    async def prefetch_records(self, model: str, ids: Set[int]) -> None:
        """Prefetch records into cache.

        Args:
            model: Model name
            ids: Set of record IDs to prefetch
        """
        if not self._cache_manager:
            return

        # Add to prefetch registry
        self.add_to_prefetch(model, ids)

        # Batch get from cache
        keys = [f"{model}:{id}" for id in ids]
        cached: Dict[CacheKey, Optional[CacheValue]] = {}
        try:
            cached = await self._cache_manager.get_many(keys)
        except (AttributeError, NotImplementedError):
            # Fallback to individual gets if get_many not supported
            for key in keys:
                try:
                    value = await self._cache_manager.get(key)
                    if value is not None:
                        cached[key] = value
                except (AttributeError, NotImplementedError):
                    continue

        # Get missing records from database
        cached_ids = {int(k.split(":")[-1]) for k in cached if cached[k] is not None}
        missing = ids - cached_ids
        if missing:
            records = await self._fetch_records(model, missing)
            # Cache missing records
            cache_data = {f"{model}:{id}": data for id, data in records.items()}
            try:
                await self._cache_manager.set_many(cache_data)
            except (AttributeError, NotImplementedError):
                # Fallback to individual sets if set_many not supported
                for key, value in cache_data.items():
                    try:
                        await self._cache_manager.set(key, value)
                    except (AttributeError, NotImplementedError):
                        continue

    async def _fetch_records(
        self, model: str, ids: Set[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Fetch records from database.

        Args:
            model: Model name
            ids: Set of record IDs to fetch

        Returns:
            Dictionary mapping record IDs to record data
        """
        if not self._registry:
            return {}

        # Get model class
        model_cls = self.get_model(model)
        if not model_cls:
            return {}

        # Convert set to list for browse
        id_list = list(ids)

        # Create model instance
        records = model_cls(self, id_list)
        if not records:
            return {}

        # Convert records to dicts
        result: Dict[int, Dict[str, Any]] = {}
        for record_id in id_list:
            record = model_cls(self, record_id)
            try:
                to_dict = getattr(record, "to_dict", None)
                if callable(to_dict):
                    result[record_id] = to_dict()
            except (AttributeError, TypeError):
                continue

        return result

    @property
    def registry(self) -> Registry[ModelLifecycle]:
        """Get registry.

        Returns:
            Registry instance

        Raises:
            RuntimeError: If registry not initialized
        """
        if not self._registry:
            raise RuntimeError("Registry not initialized")
        return self._registry

    def manage(self) -> EnvironmentManager:
        """Get environment manager.

        Returns:
            Environment manager for context management

        Examples:
            >>> async with env.manage() as env:
            ...     conn = await env.get_connection()
            ...     # Do something with connection
        """
        return EnvironmentManager(self)

    async def get_connection(self) -> Any:
        """Get database connection.

        Returns:
            Database connection from registry

        Raises:
            RuntimeError: If registry not initialized
        """
        db_registry = await container.get("database_registry")
        if not db_registry:
            raise RuntimeError("Database registry not initialized")
        return await db_registry.get_connection()

    def add_model(self, name: str, model: Type[BaseModel]) -> None:
        """Add model to environment.

        Args:
            name: Model name (e.g. "res.users")
            model: Model class

        Raises:
            ValueError: If model name already registered

        Examples:
            ```python
            @dataclass
            class User(BaseModel):
                name: str
                age: int

            env.add_model("res.users", User)
            ```
        """
        if name in self._models:
            raise ValueError(f"Model {name} already registered")
        self._models[name] = model

    def get_model(self, name: str) -> Type[BaseModel]:
        """Get model by name.

        Args:
            name: Model name (e.g. "res.users")

        Returns:
            Model class

        Raises:
            KeyError: If model not found

        Examples:
            ```python
            User = env.get_model("res.users")
            user = User(name="John", age=30)
            ```
        """
        if name not in self._models:
            raise KeyError(f"Model {name} not found")
        return self._models[name]

    def has_model(self, name: str) -> bool:
        """Check if model exists.

        Args:
            name: Model name (e.g. "res.users")

        Returns:
            True if model exists, False otherwise

        Examples:
            ```python
            if env.has_model("res.users"):
                User = env.get_model("res.users")
            ```
        """
        return name in self._models

    def __getitem__(self, name: str) -> Type[BaseModel]:
        """Get model by name using dictionary syntax.

        Args:
            name: Model name

        Returns:
            Model class

        Examples:
            ```python
            User = env["res.users"]
            ```
        """
        return self.get_model(name)

    @classmethod
    async def get_current(cls) -> "Environment":
        """Get current environment from container.

        Returns:
            Current environment instance

        Raises:
            RuntimeError: If environment not found in container
        """
        env = await container.get("environment")
        if not env:
            raise RuntimeError("Environment not found in container")
        return env

    @property
    def prefetch(self) -> Dict[str, Set[int]]:
        """Get prefetch registry.

        Returns:
            Dictionary mapping model names to sets of record IDs to prefetch
        """
        return self._prefetch

    def add_to_prefetch(self, model: str, ids: Set[int]) -> None:
        """Add record IDs to prefetch registry.

        Args:
            model: Model name
            ids: Set of record IDs to prefetch
        """
        if model not in self._prefetch:
            self._prefetch[model] = set()
        self._prefetch[model].update(ids)

    def clear_prefetch(self) -> None:
        """Clear prefetch registry."""
        self._prefetch.clear()
