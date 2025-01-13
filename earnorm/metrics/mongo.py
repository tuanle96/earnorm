"""MongoDB metrics implementation."""

import time
from abc import ABCMeta
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from ..utils.singleton import Singleton
from .base import MetricsManager


class SingletonABCMeta(Singleton, ABCMeta):
    """Metaclass combining Singleton and ABCMeta."""

    pass


class MongoMetrics(MetricsManager, metaclass=SingletonABCMeta):
    """MongoDB metrics implementation."""

    def __init__(self, uri: str, database: str) -> None:
        """Initialize metrics manager.

        Args:
            uri: MongoDB connection URI
            database: MongoDB database name
        """
        self._client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(uri)
        self._db: AsyncIOMotorDatabase[Dict[str, Any]] = self._client[database]
        self._metrics_collection: AsyncIOMotorCollection[Dict[str, Any]] = self._db[
            "metrics"
        ]

    async def track_validation(
        self,
        model: str,
        field: str,
        validator: str,
        value: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track validation result."""
        await self._metrics_collection.insert_one(
            {
                "type": "validation",
                "model": model,
                "field": field,
                "validator": validator,
                "value": value,
                "success": success,
                "error": error,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    async def track_event(
        self,
        event: str,
        model: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track event."""
        await self._metrics_collection.insert_one(
            {
                "type": "event",
                "event": event,
                "model": model,
                "success": success,
                "error": error,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    async def track_access_granted(
        self,
        user_id: str,
        model: str,
        operation: str,
    ) -> None:
        """Track access granted."""
        await self._metrics_collection.insert_one(
            {
                "type": "access",
                "user_id": user_id,
                "model": model,
                "operation": operation,
                "success": True,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    async def track_access_denied(
        self,
        user_id: str,
        model: str,
        operation: str,
        reason: str,
    ) -> None:
        """Track access denied."""
        await self._metrics_collection.insert_one(
            {
                "type": "access",
                "user_id": user_id,
                "model": model,
                "operation": operation,
                "success": False,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    async def track_db_operation(
        self,
        operation: str,
        collection: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Track database operation."""
        await self._metrics_collection.insert_one(
            {
                "type": "db_operation",
                "operation": operation,
                "collection": collection,
                "duration": duration,
                "success": success,
                "error": error,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    async def track_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool = False,
    ) -> None:
        """Track cache operation."""
        await self._metrics_collection.insert_one(
            {
                "type": "cache_operation",
                "operation": operation,
                "key": key,
                "hit": hit,
                "timestamp": datetime.now(timezone.utc),
            }
        )

    def get_metrics(
        self,
        metric_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get metrics.

        Args:
            metric_type: Type of metrics to retrieve
            start_time: Start time in Unix timestamp
            end_time: End time in Unix timestamp

        Returns:
            Dictionary containing metrics data
        """
        # Return empty metrics since this is a sync method
        # and we can't do async operations here
        return {
            "metrics": [],
            "timestamp": time.time(),
        }

    async def get_metrics_async(
        self,
        metric_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Union[List[Dict[str, Any]], float]]:
        """Get metrics asynchronously.

        Args:
            metric_type: Type of metrics to retrieve
            start_time: Start time in Unix timestamp
            end_time: End time in Unix timestamp

        Returns:
            Dictionary containing metrics data
        """
        query: Dict[str, Any] = {}

        if metric_type:
            query["type"] = metric_type

        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = datetime.fromtimestamp(
                    start_time, tz=timezone.utc
                )
            if end_time:
                query["timestamp"]["$lte"] = datetime.fromtimestamp(
                    end_time, tz=timezone.utc
                )

        cursor = self._metrics_collection.find(query)
        metrics = cast(List[Dict[str, Any]], await cursor.to_list(None))
        return {
            "metrics": metrics,
            "timestamp": time.time(),
        }
