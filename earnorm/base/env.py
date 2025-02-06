"""Environment module.

This module provides the environment class that manages the application state.
It integrates with the DI container and provides access to all services.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Type, TypeVar

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.exceptions import CacheError
from earnorm.types import DatabaseModel
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.config.data import SystemConfigData

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Environment:
    """Application environment.

    This class manages:
    - Configuration
    - Database connections
    - Model registry
    - Event bus
    - Cache management

    It integrates with the DI container and follows the singleton pattern.
    All services are accessed through the DI container.

    Examples:
        >>> env = Environment.get_instance()
        >>> await env.init(config)
        >>> adapter = await env.get_adapter()
        >>> User = env.get_model('res.users')
        >>> events = env.event_bus
    """

    # Singleton instance
    _instance: Optional["Environment"] = None

    def __init__(self) -> None:
        """Initialize environment."""
        if Environment._instance is not None:
            raise RuntimeError("Environment already initialized")

        self._initialized = False
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None

        # Cache storages
        self._cache: Dict[str, Dict[str, Dict[str, Any]]] = (
            {}
        )  # {model_name: {record_id: {field: value}}}
        self._loaded_fields: Dict[str, Dict[str, Set[str]]] = (
            {}
        )  # {model_name: {record_id: set(field_names)}}
        self._prefetch: Dict[str, Set[str]] = {}  # {model_name: set(record_ids)}
        self._max_cache_size = 10000  # Maximum number of records to cache per model

        Environment._instance = self

    def clear_cache(self, model_name: Optional[str] = None) -> None:
        """Clear cache for a model or all models.

        Args:
            model_name: Model name to clear cache for, or None for all models
        """
        if model_name:
            self._cache.pop(model_name, None)
            self._loaded_fields.pop(model_name, None)
            self._prefetch.pop(model_name, None)
        else:
            self._cache.clear()
            self._loaded_fields.clear()
            self._prefetch.clear()

    def invalidate_record(
        self, model_name: str, record_id: str, field_name: Optional[str] = None
    ) -> None:
        """Invalidate cache for a record.

        Args:
            model_name: Model name
            record_id: Record ID
            field_name: Field name to invalidate, or None for all fields
        """
        try:
            if field_name:
                # Invalidate specific field
                if model_name in self._cache and record_id in self._cache[model_name]:
                    self._cache[model_name][record_id].pop(field_name, None)
                    if (
                        model_name in self._loaded_fields
                        and record_id in self._loaded_fields[model_name]
                    ):
                        self._loaded_fields[model_name][record_id].discard(field_name)
            else:
                # Invalidate all fields
                if model_name in self._cache:
                    self._cache[model_name].pop(record_id, None)
                if model_name in self._loaded_fields:
                    self._loaded_fields[model_name].pop(record_id, None)
                if model_name in self._prefetch:
                    self._prefetch[model_name].discard(record_id)
        except Exception as e:
            logger.error(
                f"Failed to invalidate cache: {str(e)}",
                extra={
                    "model": model_name,
                    "record_id": record_id,
                    "field": field_name,
                },
            )
            raise CacheError(f"Failed to invalidate cache: {str(e)}") from e

    def is_field_loaded(self, model_name: str, record_id: str, field: str) -> bool:
        """Check if field is loaded for record.

        Args:
            model_name: Model name
            record_id: Record ID
            field: Field name

        Returns:
            bool: True if field is loaded
        """
        return (
            model_name in self._loaded_fields
            and record_id in self._loaded_fields[model_name]
            and field in self._loaded_fields[model_name][record_id]
        )

    def get_field_value(
        self, model_name: str, record_id: str, field: str
    ) -> Optional[Any]:
        """Get field value from cache.

        Args:
            model_name: Model name
            record_id: Record ID
            field: Field name

        Returns:
            Optional[Any]: Field value if cached, None otherwise
        """
        try:
            return self._cache.get(model_name, {}).get(record_id, {}).get(field)
        except Exception as e:
            logger.error(
                f"Failed to get field value from cache: {str(e)}",
                extra={"model": model_name, "record_id": record_id, "field": field},
            )
            return None

    def set_field_value(
        self, model_name: str, record_id: str, field: str, value: Any
    ) -> None:
        """Set field value in cache.

        Args:
            model_name: Model name
            record_id: Record ID
            field: Field name
            value: Field value

        Raises:
            CacheError: If cache operation fails
        """
        try:
            # Initialize cache structures if needed
            if model_name not in self._cache:
                self._cache[model_name] = {}
                self._loaded_fields[model_name] = {}

            if record_id not in self._cache[model_name]:
                # Check cache size limit
                if len(self._cache[model_name]) >= self._max_cache_size:
                    # Remove oldest records if cache is full
                    oldest_records = sorted(
                        self._cache[model_name].keys(),
                        key=lambda k: len(
                            self._loaded_fields[model_name].get(k, set())
                        ),
                    )[
                        :100
                    ]  # Remove 100 oldest records
                    for old_id in oldest_records:
                        self._cache[model_name].pop(old_id, None)
                        self._loaded_fields[model_name].pop(old_id, None)

                self._cache[model_name][record_id] = {}
                self._loaded_fields[model_name][record_id] = set()

            # Set value and mark field as loaded
            self._cache[model_name][record_id][field] = value
            self._loaded_fields[model_name][record_id].add(field)

        except Exception as e:
            logger.error(
                f"Failed to set field value in cache: {str(e)}",
                extra={
                    "model": model_name,
                    "record_id": record_id,
                    "field": field,
                    "value": value,
                },
            )
            raise CacheError(f"Failed to set field value in cache: {str(e)}") from e

    def mark_for_prefetch(self, model_name: str, record_ids: List[str]) -> None:
        """Mark records for prefetching.

        Args:
            model_name: Model name
            record_ids: Record IDs to prefetch
        """
        if model_name not in self._prefetch:
            self._prefetch[model_name] = set()
        self._prefetch[model_name].update(record_ids)

    def get_prefetch_ids(self, model_name: str) -> Set[str]:
        """Get record IDs marked for prefetching.

        Args:
            model_name: Model name

        Returns:
            Set[str]: Record IDs marked for prefetching
        """
        return self._prefetch.get(model_name, set())

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict[str, Any]: Cache statistics
        """
        stats: Dict[str, Any] = {
            "models": len(self._cache),
            "total_records": sum(len(records) for records in self._cache.values()),
            "total_fields": sum(
                sum(len(fields) for fields in model_records.values())
                for model_records in self._cache.values()
            ),
            "models_stats": {},
        }

        for model_name, records in self._cache.items():
            model_stats = {
                "records": len(records),
                "fields": sum(len(fields) for fields in records.values()),
                "loaded_fields": sum(
                    len(fields)
                    for fields in self._loaded_fields.get(model_name, {}).values()
                ),
                "prefetch_count": len(self._prefetch.get(model_name, set())),
            }
            stats["models_stats"][model_name] = model_stats

        return stats

    async def prefetch_all_pending(self) -> None:
        """Prefetch all pending records marked for prefetch."""
        for model_name, record_ids in self._prefetch.items():
            if record_ids:
                model_class = await self.get_model(model_name)
                records = await model_class.browse(list(record_ids))  # type: ignore
                # Prefetch common fields
                fields = list(model_class.__fields__.keys())  # type: ignore
                await records._prefetch_records(fields)  # type: ignore
                # Clear prefetch queue
                record_ids.clear()

    def optimize_cache(self, max_records: int = 1000) -> None:
        """Optimize cache size by removing least recently used records.

        Args:
            max_records: Maximum number of records to keep per model
        """
        for model_name, records in self._cache.items():
            if len(records) > max_records:
                # Get least recently used records
                sorted_records = sorted(
                    records.items(),
                    key=lambda x: (
                        max(
                            field_set
                            for field_set in self._loaded_fields[model_name][x[0]]
                        )
                        if self._loaded_fields[model_name][x[0]]
                        else 0
                    ),
                )

                # Remove excess records
                excess = len(records) - max_records
                for record_id, _ in sorted_records[:excess]:
                    self.invalidate_record(model_name, record_id)

    @classmethod
    def get_instance(cls) -> "Environment":
        """Get singleton instance.

        Returns:
            Environment instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init(self, config: "SystemConfigData") -> None:
        """Initialize environment.

        Args:
            config: System configuration data

        This method:
        1. Registers config in DI container
        2. Initializes services through DI container
        3. Sets up service dependencies
        """
        if self._initialized:
            logger.warning("Environment already initialized")
            return

        try:
            from earnorm.di import container

            # Register config
            container.register("config", config)

            # Get services from DI container
            self._adapter = await container.get("database_adapter")

            # Register self in container
            container.register("env", self)

            self._initialized = True
            logger.info("Environment initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize environment: %s", str(e))
            raise RuntimeError(f"Environment initialization failed: {e}") from e

    async def destroy(self) -> None:
        """Cleanup environment.

        This method:
        1. Closes database connections
        2. Stops event bus
        """
        if not self._initialized:
            return

        try:
            from earnorm.di import container

            # Get services from DI container
            if container.has("database_adapter"):
                adapter = await container.get("database_adapter")
                await adapter.close()

            # check if event bus is registered
            if container.has("event_bus"):
                events = await container.get("event_bus")
                await events.destroy()

            # Reset state
            self._initialized = False

            logger.info("Environment cleaned up successfully")

        except Exception as e:
            logger.error("Failed to cleanup environment: %s", str(e))
            raise RuntimeError(f"Environment cleanup failed: {e}") from e

    async def get_service(self, name: str, required: bool = True) -> Any:
        """Get service from DI container.

        Args:
            name: Service name
            required: Whether service is required

        Returns:
            Service instance

        Raises:
            RuntimeError: If service not found and required=True
        """
        from earnorm.di import container

        service = await container.get(name)
        if service is None and required:
            raise RuntimeError(f"Service {name} not found in DI container")
        return service

    @property
    def adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter synchronously.

        Returns:
            Database adapter instance

        Raises:
            RuntimeError: If adapter not initialized
        """
        if not self._initialized:
            raise RuntimeError("Environment not initialized")
        if self._adapter is None:
            raise RuntimeError("Adapter not initialized. Call init() first")
        return self._adapter

    async def get_model(self, name: str) -> Type[ModelProtocol]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class implementing ModelProtocol

        Raises:
            ValueError: If model not found
        """
        model = await self.get_service(f"model.{name}", required=False)
        if model is None:
            raise ValueError(f"Model {name} not found")
        return model
