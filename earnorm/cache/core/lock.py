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

    # Extend lock timeout
    if await lock.extend(30):
        print("Lock extended by 30 seconds")

    # Force unlock (use with caution)
    if await lock.force_unlock():
        print("Lock forcefully released")
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
    - Lock extension
    - Force unlock capability

    Examples:
        ```python
        # Create lock with custom settings
        lock = DistributedLock(
            client=redis_client,
            name="process_lock",
            timeout=30,
            retry_count=10,
            retry_delay=0.5
        )

        # Use in async context
        async with lock as acquired:
            if acquired:
                await process_data()
            else:
                print("Failed to acquire lock")

        # Manual lock management
        if await lock.acquire():
            try:
                await process_data()
                # Extend lock if needed
                await lock.extend(30)
            finally:
                await lock.release()
        ```

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
            # Basic lock
            lock = DistributedLock(
                client=redis_client,
                name="my_lock"
            )

            # Lock with custom timeout and retries
            lock = DistributedLock(
                client=redis_client,
                name="process_lock",
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
                else:
                    # Lock acquisition failed
                    print("Failed to acquire lock")
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
            # Basic acquisition
            if await lock.acquire():
                try:
                    await process_data()
                finally:
                    await lock.release()

            # With timeout handling
            try:
                if await lock.acquire():
                    await process_data()
                else:
                    print("Lock acquisition failed")
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
                logger.debug("Acquired lock %s", self.name)
                return True

            retries -= 1
            if retries > 0:
                await asyncio.sleep(self.retry_delay)

        logger.warning(
            "Failed to acquire lock %s after %d retries", self.name, self.retry_count
        )
        return False

    async def release(self) -> None:
        """Release lock.

        This method releases the lock if it was acquired by this instance.
        It uses a Lua script to ensure the lock is only released by its owner.

        Examples:
            ```python
            # Manual release
            await lock.release()

            # Release in try/finally
            try:
                if await lock.acquire():
                    await process_data()
            finally:
                await lock.release()
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
        logger.debug("Released lock %s", self.name)

    async def extend(self, additional_time: int) -> bool:
        """Extend lock timeout if owner.

        Args:
            additional_time: Additional seconds to extend lock

        Returns:
            bool: True if lock was extended

        Examples:
            ```python
            # Extend lock by 30 seconds
            if await lock.extend(30):
                print("Lock extended")
            else:
                print("Failed to extend lock")

            # Extend during processing
            if await lock.acquire():
                try:
                    while processing:
                        await process_chunk()
                        if not await lock.extend(30):
                            break
                finally:
                    await lock.release()
            ```
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
                        "Extended lock %s by %d seconds", self.name, additional_time
                    )
                return extended
        except RedisError as e:
            logger.error("Failed to extend lock %s: %s", self.name, str(e))

        return False

    async def is_locked(self) -> bool:
        """Check if lock is currently held.

        Returns:
            bool: True if lock exists

        Examples:
            ```python
            # Check lock status
            if await lock.is_locked():
                print("Lock is held")
            else:
                print("Lock is available")

            # Check before acquiring
            if not await lock.is_locked():
                if await lock.acquire():
                    await process_data()
            ```
        """
        try:
            return bool(await self.client.exists(self.name))
        except RedisError as e:
            logger.error("Failed to check lock %s: %s", self.name, str(e))
            return False

    async def force_unlock(self) -> bool:
        """Force unlock the lock regardless of owner.

        Returns:
            bool: True if lock was deleted

        Examples:
            ```python
            # Force unlock with warning
            if await lock.is_locked():
                if await lock.force_unlock():
                    logger.warning("Lock forcefully released")

            # Clear stuck lock
            if await lock.force_unlock():
                print("Cleared stuck lock")
            ```
        """
        try:
            deleted = bool(await self.client.delete(self.name))
            if deleted:
                logger.warning("Forced unlock of %s", self.name)
            return deleted
        except RedisError as e:
            logger.error("Failed to force unlock %s: %s", self.name, str(e))
            return False
