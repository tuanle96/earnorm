"""Log streaming for streaming log entries."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Set


class LogStream:
    """Class for streaming log entries.

    This class provides functionality to:
    - Stream log entries in real-time
    - Filter log entries
    - Buffer log entries
    - Batch log entries

    Examples:
        >>> # Stream all logs
        >>> stream = LogStream()
        >>> async for entry in stream:
        ...     print(f'Got log: {entry}')

        >>> # Stream with filtering
        >>> stream = LogStream(
        ...     levels={'error', 'critical'},
        ...     fields={'service': 'api'}
        ... )
        >>> async for entry in stream:
        ...     print(f'Got error: {entry}')

        >>> # Stream with batching
        >>> stream = LogStream(batch_size=10)
        >>> async for batch in stream:
        ...     print(f'Got batch of {len(batch)} logs')

        >>> # Stream with timeout
        >>> stream = LogStream(
        ...     batch_size=10,
        ...     batch_timeout=5.0
        ... )
        >>> async for batch in stream:
        ...     print(f'Got batch after {batch[0]["batch_time"]}s')
    """

    def __init__(
        self,
        levels: Optional[Set[str]] = None,
        fields: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        batch_timeout: Optional[float] = None,
        buffer_size: int = 1000,
    ):
        """Initialize the log stream.

        Args:
            levels: Set of log levels to include.
            fields: Dict of field values to match.
            batch_size: Number of logs per batch.
            batch_timeout: Max seconds to wait for batch.
            buffer_size: Max size of internal buffer.
        """
        self.levels = {level.lower() for level in (levels or [])}
        self.fields = fields or {}
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.buffer_size = buffer_size

        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=buffer_size)
        self._batch: List[Dict[str, Any]] = []
        self._batch_start: Optional[datetime] = None

    def _matches_filters(self, log_entry: Dict[str, Any]) -> bool:
        """Check if a log entry matches the filters.

        Args:
            log_entry: The log entry to check.

        Returns:
            bool: True if the entry matches all filters.
        """
        # Check level filter
        if self.levels:
            level = str(log_entry.get("level", "")).lower()
            if level not in self.levels:
                return False

        # Check field filters
        for field, value in self.fields.items():
            if log_entry.get(field) != value:
                return False

        return True

    async def put(self, log_entry: Dict[str, Any]) -> None:
        """Add a log entry to the stream.

        Args:
            log_entry: The log entry to add.
        """
        if self._matches_filters(log_entry):
            try:
                await self._queue.put(log_entry)
            except asyncio.QueueFull:
                # Drop oldest entry if queue is full
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                await self._queue.put(log_entry)

    async def _get_next_batch(self) -> List[Dict[str, Any]]:
        """Get the next batch of log entries.

        Returns:
            List[Dict[str, Any]]: The next batch of entries.
        """
        # Start new batch
        if not self._batch:
            self._batch = []
            self._batch_start = datetime.now()

        # Get entries until batch is full or times out
        while True:
            # Check if batch is complete
            if self.batch_size and len(self._batch) >= self.batch_size:
                break

            # Check if batch has timed out
            if self.batch_timeout and self._batch_start:
                elapsed = datetime.now() - self._batch_start
                if elapsed > timedelta(seconds=self.batch_timeout):
                    break

            # Try to get next entry
            try:
                timeout = None
                if self.batch_timeout and self._batch_start:
                    elapsed = datetime.now() - self._batch_start
                    remaining = timedelta(seconds=self.batch_timeout) - elapsed
                    if remaining.total_seconds() <= 0:
                        break
                    timeout = remaining.total_seconds()

                entry = await asyncio.wait_for(self._queue.get(), timeout=timeout)
                self._batch.append(entry)
                self._queue.task_done()

            except asyncio.TimeoutError:
                break

        # Add batch metadata
        if self._batch and self._batch_start:
            elapsed = datetime.now() - self._batch_start
            for entry in self._batch:
                entry["batch_size"] = len(self._batch)
                entry["batch_time"] = elapsed.total_seconds()

        # Return batch and reset
        batch = self._batch
        self._batch = []
        self._batch_start = None
        return batch

    def __aiter__(self) -> AsyncIterator[Any]:
        """Return async iterator for the stream.

        Returns:
            AsyncIterator[Any]: Iterator of log entries or batches.
        """
        return self

    async def __anext__(self) -> Any:
        """Get next item from the stream.

        Returns:
            Any: Next log entry or batch.

        Raises:
            StopAsyncIteration: If stream is closed.
        """
        try:
            if self.batch_size or self.batch_timeout:
                batch = await self._get_next_batch()
                if not batch:
                    raise StopAsyncIteration
                return batch
            else:
                return await self._queue.get()

        except asyncio.CancelledError:
            raise StopAsyncIteration
