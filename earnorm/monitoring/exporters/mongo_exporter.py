"""MongoDB metrics exporter."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, TypedDict, cast

from earnorm.events.core import EventBus
from earnorm.events.core.event import Event
from earnorm.monitoring.exporters import BaseExporter
from earnorm.monitoring.metrics import Metric
from earnorm.pool import MongoPool
from earnorm.pool.protocols.connection import ConnectionProtocol

logger = logging.getLogger(__name__)


class MetricLabels(TypedDict, total=False):
    """Labels for a metric."""

    host: str
    instance: str
    job: str
    service: str
    environment: str


class MetricDocument(TypedDict):
    """MongoDB document for a metric."""

    name: str
    description: Optional[str]  # Description can be None
    value: float
    labels: MetricLabels
    timestamp: datetime


class MongoExporter(BaseExporter):
    """MongoDB metrics exporter.

    Examples:
        >>> from earnorm.pool import MongoPool
        >>> pool = MongoPool(uri="mongodb://localhost:27017", database="metrics")
        >>> exporter = MongoExporter(pool=pool, collection="metrics")
        >>> # Export metrics
        >>> metrics = [
        ...     Counter("requests_total", "Total requests", value=100),
        ...     Gauge("cpu_usage", "CPU usage", value=0.75),
        ... ]
        >>> await exporter.export_metrics(metrics)
        >>> # Metrics are now stored in MongoDB
    """

    def __init__(
        self,
        pool: MongoPool,
        collection: str,
        event_bus: Optional[EventBus] = None,
        batch_size: int = 1000,
    ) -> None:
        """Initialize MongoDB exporter.

        Args:
            pool: MongoDB connection pool
            collection: Collection name for metrics
            event_bus: Event bus for emitting metrics
            batch_size: Maximum number of documents to insert in one batch
        """
        super().__init__("mongodb")
        self._pool = pool
        self._collection = collection
        self._event_bus = event_bus
        self._batch_size = batch_size

    async def export_metrics(self, metrics: Sequence[Metric]) -> None:
        """Export metrics to MongoDB.

        Args:
            metrics: List of metrics to export

        Raises:
            Exception: If exporting metrics fails
        """
        try:
            # Convert metrics to documents
            documents: List[MetricDocument] = []
            timestamp = datetime.now(timezone.utc)

            for metric in metrics:
                # Get labels with default empty dict if not present
                labels = cast(MetricLabels, getattr(metric, "labels", {}))

                document = MetricDocument(
                    name=metric.name,
                    description=metric.description,
                    value=metric.value,
                    labels=labels,
                    timestamp=timestamp,
                )
                documents.append(document)

                # Insert batch if size limit reached
                if len(documents) >= self._batch_size:
                    conn: ConnectionProtocol = await self._pool.acquire()
                    try:
                        await conn.execute("insert_many", self._collection, documents)
                    finally:
                        await conn.close()
                    documents = []

            # Insert remaining documents
            if documents:
                conn: ConnectionProtocol = await self._pool.acquire()
                try:
                    await conn.execute("insert_many", self._collection, documents)
                finally:
                    await conn.close()

            # Emit metrics exported event
            if self._event_bus:
                event_data: Dict[str, Any] = {
                    "exporter": self.name,
                    "collection": self._collection,
                    "metrics_count": len(metrics),
                    "timestamp": timestamp.isoformat(),
                }
                event = Event(name="metrics.exported", data=event_data)
                await self._event_bus.publish(event)

            logger.debug(
                "Exported %d metrics to MongoDB collection %s",
                len(metrics),
                self._collection,
            )
        except Exception as e:
            logger.exception(
                "Error exporting metrics to MongoDB collection %s: %s",
                self._collection,
                e,
            )
            raise

    async def get_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metrics: Optional[Sequence[str]] = None,
    ) -> Dict[str, List[float]]:
        """Get metrics from MongoDB.

        Args:
            start_time: Start time
            end_time: End time
            metrics: Optional list of metric names to get

        Returns:
            Dictionary mapping metric names to lists of values

        Raises:
            Exception: If getting metrics fails
        """
        try:
            conn: ConnectionProtocol = await self._pool.acquire()
            try:
                # Build query
                query: Dict[str, Any] = {
                    "timestamp": {"$gte": start_time, "$lte": end_time}
                }
                if metrics:
                    query["name"] = {"$in": list(metrics)}

                # Get metrics
                cursor = await conn.execute(
                    "find", self._collection, query, sort=[("timestamp", 1)]
                )

                # Group metrics by name
                results: Dict[str, List[float]] = {}
                async for doc in cursor:
                    name = doc["name"]
                    value = doc["value"]
                    if name not in results:
                        results[name] = []
                    results[name].append(value)

                return results
            finally:
                await conn.close()
        except Exception as e:
            logger.exception(
                "Error getting metrics from MongoDB collection %s: %s",
                self._collection,
                e,
            )
            raise
