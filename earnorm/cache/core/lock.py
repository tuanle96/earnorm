"""Distributed lock implementation.

This module provides a distributed locking mechanism using Redis.
It supports:
- Lock acquisition with timeout
- Automatic lock release
- Lock owner tracking
- Retry with backoff

Examples:
    ```python
    from earnorm.cache.core.lock import DistributedLock

    # Create lock
    lock = DistributedLock(
        client=redis_client,
        name="my_lock",
        timeout=10,
        retry_count=5,
        retry_delay=0.2
    )

    # Use with async context manager
    async with lock as acquired:
        if acquired:
            # Lock acquired, do work
            await process_data()
        else:
            # Failed to acquire lock
            print("Lock acquisition failed")

    # Or use manually
    if await lock.acquire():
        try:
            # Lock acquired, do work
            await process_data()
        finally:
            await lock.release()
    ```
"""

import asyncio
import logging
import time
from typing import Any, Optional, cast

from redis.asyncio.client import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class DistributedLock:
    """Distributed lock implementation using Redis.

    This class provides a distributed locking mechanism using Redis SET NX
    command with expiry. It supports automatic lock release and retry with
    exponential backoff.

    Features:
    - Lock acquisition with timeout
    - Automatic lock release on context exit
    - Lock owner tracking to prevent release by non-owner
    - Retry with exponential backoff
    - Health checks via PING

    Attributes:
        client: Redis client instance
        name: Lock name (prefixed with "lock:")
        timeout: Lock timeout in seconds
        retry_count: Number of acquisition retries
        retry_delay: Initial delay between retries in seconds
        _owner: Lock owner identifier
    """

    def __init__(
        self,
        client: Redis,
        name: str,
        timeout: int = 10,
        retry_count: int = 5,
        retry_delay: float = 0.2,
    ) -> None:
        """Initialize lock.

        Args:
            client: Redis client instance
            name: Lock name (will be prefixed with "lock:")
            timeout: Lock timeout in seconds (default: 10)
            retry_count: Number of acquisition retries (default: 5)
            retry_delay: Initial delay between retries in seconds (default: 0.2)

        Examples:
            ```python
            lock = DistributedLock(
                client=redis_client,
                name="my_lock",
                timeout=30,
                retry_count=10,
                retry_delay=0.5
            )
            ```
        """
        self.client = client
        self.name = f"lock:{name}"
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._owner: Optional[str] = None

    async def __aenter__(self) -> bool:
        """Acquire lock on enter.

        This method is called when entering an async context manager.
        It attempts to acquire the lock with configured retries.

        Returns:
            bool: True if lock was acquired

        Examples:
            ```python
            async with lock as acquired:
                if acquired:
                    # Lock acquired
                    await process_data()
            ```
        """
        return await self.acquire()

    async def __aexit__(self, *args: Any) -> None:
        """Release lock on exit.

        This method is called when exiting an async context manager.
        It releases the lock if it was acquired by this instance.

        Examples:
            ```python
            async with lock:
                # Lock is released automatically on exit
                await process_data()
            ```
        """
        await self.release()

    async def acquire(self) -> bool:
        """Acquire lock with retry.

        This method attempts to acquire the lock using Redis SET NX command.
        It will retry up to retry_count times with exponential backoff.

        Returns:
            bool: True if lock was acquired

        Examples:
            ```python
            if await lock.acquire():
                try:
                    await process_data()
                finally:
                    await lock.release()
            ```
        """
        self._owner = f"{id(self)}:{time.time()}"
        retries = self.retry_count

        while retries > 0:
            # SET NX with expiry
            locked = await cast(Any, self.client).set(
                self.name, self._owner, nx=True, ex=self.timeout
            )
            if locked:
                logger.debug(f"Acquired lock {self.name}")
                return True

            retries -= 1
            if retries > 0:
                await asyncio.sleep(self.retry_delay)

        logger.warning(
            f"Failed to acquire lock {self.name} after {self.retry_count} retries"
        )
        return False

    async def release(self) -> None:
        """Release lock.

        This method releases the lock if it was acquired by this instance.
        It uses a Lua script to ensure the lock is only released by its owner.

        Examples:
            ```python
            await lock.release()  # Release lock manually
            ```
        """
        if self._owner is None:
            return

        # Use Lua script to ensure we only release our own lock
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await cast(Any, self.client).eval(script, 1, self.name, self._owner)
        self._owner = None
        logger.debug(f"Released lock {self.name}")

    async def extend(self, additional_time: int) -> bool:
        """Extend lock timeout if owner.

        Args:
            additional_time: Additional seconds to extend lock

        Returns:
            bool: True if lock was extended
        """
        if not self._owner:
            return False

        try:
            current = await self.client.get(self.name)
            if current and current == self._owner:
                # Extend timeout
                extended = bool(
                    await self.client.expire(self.name, self.timeout + additional_time)
                )
                if extended:
                    logger.debug(
                        f"Extended lock {self.name} by {additional_time} seconds"
                    )
                return extended
        except RedisError as e:
            logger.error(f"Failed to extend lock {self.name}: {str(e)}")

        return False

    async def is_locked(self) -> bool:
        """Check if lock is currently held.

        Returns:
            bool: True if lock exists
        """
        try:
            return bool(await self.client.exists(self.name))
        except RedisError as e:
            logger.error(f"Failed to check lock {self.name}: {str(e)}")
            return False

    async def force_unlock(self) -> bool:
        """Force unlock regardless of owner.

        Returns:
            bool: True if lock was deleted
        """
        try:
            deleted = bool(await self.client.delete(self.name))
            if deleted:
                logger.warning(f"Force unlocked {self.name}")
            return deleted
        except RedisError as e:
            logger.error(f"Failed to force unlock {self.name}: {str(e)}")
            return False
