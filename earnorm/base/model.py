"""Base model for EarnORM."""

from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar, cast

from ..di.container import container
from .types import AclDict, AclManager, AuditConfig
from .types import BaseModel as BaseModelProtocol
from .types import (
    CacheConfig,
    ConstraintFunc,
    IndexDict,
    JsonEncoders,
    MetricsConfig,
    MetricsManager,
    PoolManager,
    RuleDict,
    RuleManager,
    ValidatorFunc,
)

T = TypeVar("T", bound="BaseModel")


class BaseModel(BaseModelProtocol):
    """Base model for EarnORM.

    Provides core functionality for models:
    - Database operations
    - Validation
    - Access control
    - Caching
    - Events
    - Metrics
    """

    # Model configuration
    _collection: str = ""
    _data: Dict[str, Any] = {}
    _indexes: IndexDict = {}
    _validators: List[ValidatorFunc[Any]] = []
    _constraints: List[ConstraintFunc[Any]] = []
    _acl: AclDict = {}
    _rules: RuleDict = {}
    _events: Dict[str, List[ValidatorFunc[Any]]] = {}
    _audit: AuditConfig = {}
    _cache: CacheConfig = {}
    _metrics: MetricsConfig = {}
    _json_encoders: JsonEncoders = {}

    def __init__(self, **data: Any) -> None:
        """Initialize model.

        Args:
            **data: Model data
        """
        self._data = data

    @classmethod
    def get_collection(cls) -> str:
        """Get collection name.

        Returns:
            Collection name
        """
        return cls._collection

    async def save(self) -> None:
        """Save model to database."""
        # Get collection
        pool_manager = cast(PoolManager, await container.get("pool_manager"))
        collection = await pool_manager.get_collection(self._collection)

        # Validate data
        await self._validate()

        # Check access
        await self._check_access()

        # Run before save hooks
        await self._run_hooks("before_save")

        # Save to database
        if "_id" in self._data:
            await collection.update_one(
                {"_id": self._data["_id"]}, {"$set": self._data}
            )
        else:
            result = await collection.insert_one(self._data)
            self._data["_id"] = result.inserted_id

        # Run after save hooks
        await self._run_hooks("after_save")

        # Track metrics
        metrics_manager = cast(MetricsManager, await container.get("metrics_manager"))
        await metrics_manager.track_operation("save", self._collection, self._metrics)

    async def delete(self) -> None:
        """Delete model from database."""
        # Get collection
        pool_manager = cast(PoolManager, await container.get("pool_manager"))
        collection = await pool_manager.get_collection(self._collection)

        # Check access
        await self._check_access()

        # Run before delete hooks
        await self._run_hooks("before_delete")

        # Delete from database
        await collection.delete_one({"_id": self._data["_id"]})

        # Run after delete hooks
        await self._run_hooks("after_delete")

        # Track metrics
        metrics_manager = cast(MetricsManager, await container.get("metrics_manager"))
        await metrics_manager.track_operation("delete", self._collection, self._metrics)

    @classmethod
    async def find_one(cls: Type[T], filter_: Dict[str, Any]) -> Optional[T]:
        """Find single document.

        Args:
            filter_: Query filter

        Returns:
            Model instance or None if not found
        """
        # Get collection
        pool_manager = cast(PoolManager, await container.get("pool_manager"))
        collection = await pool_manager.get_collection(cls._collection)

        # Find document
        doc = await collection.find_one(filter_)
        if doc is None:
            return None

        # Create model instance
        return cls(**doc)

    @classmethod
    async def find(cls: Type[T], filter_: Dict[str, Any]) -> Sequence[T]:
        """Find multiple documents.

        Args:
            filter_: Query filter

        Returns:
            List of model instances
        """
        # Get collection
        pool_manager = cast(PoolManager, await container.get("pool_manager"))
        collection = await pool_manager.get_collection(cls._collection)

        # Find documents
        docs = await collection.find(filter_).to_list(None)

        # Create model instances
        return [cls(**doc) for doc in docs]

    async def _validate(self) -> None:
        """Validate model data."""
        # Run validators
        for validator in self._validators:
            await validator(self)

        # Run constraints
        for constraint in self._constraints:
            await constraint(self)

    async def _check_access(self) -> None:
        """Check access control."""
        # Check ACL
        acl_manager = cast(AclManager, await container.get("acl_manager"))
        await acl_manager.check_access(self)

        # Check rules
        rule_manager = cast(RuleManager, await container.get("rule_manager"))
        await rule_manager.check_rules(self)

    async def _run_hooks(self, event: str) -> None:
        """Run lifecycle hooks.

        Args:
            event: Event name
        """
        if event in self._events:
            hooks = self._events[event]
            for hook in hooks:
                await hook(self)
