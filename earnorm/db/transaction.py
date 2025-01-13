"""Transaction management for EarnORM."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, TypeVar

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo.errors import ConnectionFailure, OperationFailure

from .connection import ConnectionManager

T = TypeVar("T")


class TransactionManager:
    """Manager for database transactions."""

    def __init__(self) -> None:
        """Initialize transaction manager."""
        self._conn = ConnectionManager()
        self._active_sessions: Dict[int, AsyncIOMotorClientSession] = {}

    async def _get_session(self) -> AsyncIOMotorClientSession:
        """Get session for current task."""
        task_id = id(asyncio.current_task())
        if task_id not in self._active_sessions:
            if not self._conn.is_connected():
                raise ConnectionError("Not connected to database")
            client = self._conn._client
            if client is None:
                raise ConnectionError("Not connected to database")
            session = await client.start_session()
            self._active_sessions[task_id] = session
        return self._active_sessions[task_id]

    async def _end_session(self) -> None:
        """End session for current task."""
        task_id = id(asyncio.current_task())
        if task_id in self._active_sessions:
            session = self._active_sessions[task_id]
            await session.end_session()
            del self._active_sessions[task_id]

    @asynccontextmanager
    async def transaction(
        self,
        *,
        read_concern: Optional[Dict[str, Any]] = None,
        write_concern: Optional[Dict[str, Any]] = None,
        read_preference: Optional[str] = None,
        max_commit_time_ms: Optional[int] = None,
    ) -> AsyncGenerator[AsyncIOMotorClientSession, None]:
        """Start a transaction.

        Args:
            read_concern: Read concern options
            write_concern: Write concern options
            read_preference: Read preference
            max_commit_time_ms: Max commit time in milliseconds

        Yields:
            Session: The transaction session

        Raises:
            ConnectionError: If not connected to database
            OperationFailure: If transaction fails
        """
        session = await self._get_session()

        options: Dict[str, Any] = {}
        if read_concern is not None:
            options["read_concern"] = read_concern
        if write_concern is not None:
            options["write_concern"] = write_concern
        if read_preference is not None:
            options["read_preference"] = read_preference
        if max_commit_time_ms is not None:
            options["max_commit_time_ms"] = max_commit_time_ms

        try:
            await session.start_transaction(**options)
            yield session
            await session.commit_transaction()
        except (ConnectionFailure, OperationFailure):
            await session.abort_transaction()
            raise
        finally:
            await self._end_session()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncIOMotorClientSession, None]:
        """Start a session without transaction.

        Yields:
            Session: The session

        Raises:
            ConnectionError: If not connected to database
        """
        session = await self._get_session()
        try:
            yield session
        finally:
            await self._end_session()

    async def commit(self, session: AsyncIOMotorClientSession) -> None:
        """Commit transaction.

        Args:
            session: The session to commit

        Raises:
            OperationFailure: If commit fails
        """
        await session.commit_transaction()

    async def abort(self, session: AsyncIOMotorClientSession) -> None:
        """Abort transaction.

        Args:
            session: The session to abort
        """
        await session.abort_transaction()

    def is_in_transaction(self, session: AsyncIOMotorClientSession) -> bool:
        """Check if session is in transaction.

        Args:
            session: The session to check

        Returns:
            bool: True if in transaction
        """
        return bool(session.in_transaction)

    def get_transaction_options(
        self, session: AsyncIOMotorClientSession
    ) -> Dict[str, Any]:
        """Get transaction options.

        Args:
            session: The session to get options from

        Returns:
            dict: Transaction options
        """
        return session.options  # type: ignore
