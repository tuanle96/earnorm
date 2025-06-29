"""MongoDB connection pool implementation."""

import asyncio
import logging
from typing import Any, AsyncContextManager, TypeVar, cast
from urllib.parse import urlparse

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

# pylint: disable=redefined-builtin
from earnorm.exceptions import MongoDBConnectionError, PoolExhaustedError
from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol
from earnorm.pool.protocols.pool import AsyncPoolProtocol

DB = TypeVar("DB", bound=AsyncIOMotorDatabase[dict[str, Any]])
COLL = TypeVar("COLL", bound=AsyncIOMotorCollection[dict[str, Any]])

logger = logging.getLogger(__name__)

# MongoDB URI pattern
# Format: mongodb[+srv]://[username:password@]host1[:port1][,...hostN[:portN]][/[database][?options]]
MONGODB_URI_PATTERN = (
    r"^mongodb(?:\+srv)?://"  # Scheme (mongodb:// or mongodb+srv://)
    r"(?:(?:[^:/@]+)?(?::(?:[^:/@]+)?)?@)?"  # Optional username:password@
    r"[^/?@]+"  # Required host(s)
    r"(?:/(?:[^?]+))?"  # Optional /database
    r"(?:\?(?:[^#]+))?"  # Optional query parameters
    r"$"
)


class _ConnectionManager(AsyncContextManager[AsyncConnectionProtocol[DB, COLL]]):
    """Connection manager context."""

    def __init__(self, pool: "MongoPool[DB, COLL]") -> None:
        """Initialize connection manager.

        Args:
            pool: Pool instance
        """
        self._pool = pool
        self._conn: AsyncConnectionProtocol[DB, COLL] | None = None

    async def __aenter__(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Enter context.

        Returns:
            AsyncConnectionProtocol: Connection instance
        """
        self._conn = await self._pool.acquire()
        return self._conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context."""
        if self._conn:
            await self._pool.release(self._conn)


class MongoPool(AsyncPoolProtocol[DB, COLL]):
    """MongoDB connection pool implementation."""

    def __init__(
        self,
        uri: str,
        database: str,
        min_size: int = 1,
        max_size: int = 10,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize pool.

        Args:
            uri: MongoDB URI
            database: Database name
            min_size: Minimum pool size
            max_size: Maximum pool size
            retry_policy: Optional retry policy
            circuit_breaker: Optional circuit breaker
            **kwargs: Additional client options

        Raises:
            ValueError: If URI is invalid or required parameters are missing
        """
        if not uri:
            raise ValueError("MongoDB URI cannot be empty")

        # Log input parameters
        logger.debug("Initializing MongoPool with URI: %s", uri)
        logger.debug("URI type: %s, length: %d", type(uri), len(uri))
        logger.debug("Database: %s", database)

        # Parse and validate URI
        try:
            # Try to parse the URI
            parsed = urlparse(uri)

            # Log parsed components
            logger.debug("Parsed URI components:")
            logger.debug("- scheme: '%s'", parsed.scheme)
            logger.debug("- netloc: '%s'", parsed.netloc)
            logger.debug("- path: '%s'", parsed.path)
            logger.debug("- params: '%s'", parsed.params)
            logger.debug("- query: '%s'", parsed.query)
            logger.debug("- fragment: '%s'", parsed.fragment)

            # Validate scheme
            if not parsed.scheme:
                raise ValueError("MongoDB URI must have a scheme")
            if parsed.scheme != "mongodb":
                raise ValueError(f"Invalid MongoDB URI scheme: {parsed.scheme}")

            # Validate host and port
            if not parsed.netloc:
                raise ValueError("MongoDB URI must contain a valid hostname")

            # Extract host and port
            host_parts = parsed.netloc.split(":")
            if len(host_parts) > 1:
                try:
                    port = int(host_parts[1])
                    if not 1 <= port <= 65535:
                        raise ValueError(f"Invalid port number: {port}")
                except ValueError as e:
                    raise ValueError(f"Invalid port in MongoDB URI: {host_parts[1]}") from e

            # Validate path (database name)
            if parsed.path and parsed.path != "/":
                db_name = parsed.path.strip("/")
                if db_name and db_name != database:
                    logger.warning(
                        "Database name in URI (%s) differs from provided database name (%s). Using provided database name.",
                        db_name,
                        database,
                    )

            logger.debug("MongoDB URI validation passed")

        except Exception as e:
            logger.error("MongoDB URI validation failed: %s", str(e))
            raise ValueError(
                f"Invalid MongoDB URI format: {e!s}. Expected format: mongodb://host[:port]/[database][?options]"
            ) from e

        self._uri = uri
        self._database = database
        self._min_size = min_size
        self._max_size = max_size
        self._retry_policy = retry_policy or RetryPolicy()
        self._circuit_breaker = circuit_breaker
        self._kwargs = kwargs

        self._client: AsyncIOMotorClient[dict[str, Any]] | None = None
        self._available: set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._in_use: set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._lock = asyncio.Lock()

    def _map_options(self, options: dict[str, Any]) -> dict[str, Any]:
        """Map configuration options to PyMongo client options.

        Args:
            options: Configuration options

        Returns:
            Dict[str, Any]: PyMongo client options with mapped keys and values
        """
        option_mapping = {
            "server_selection_timeout_ms": "serverSelectionTimeoutMS",
            "connect_timeout_ms": "connectTimeoutMS",
            "socket_timeout_ms": "socketTimeoutMS",
            "retry_writes": "retryWrites",
            "retry_reads": "retryReads",
            "w": "w",
            "j": "journal",
        }

        client_options: dict[str, Any] = {}
        for key, value in options.items():
            if key in option_mapping:
                client_options[option_mapping[key]] = value
                logger.debug("Mapped option %s -> %s: %s", key, option_mapping[key], value)

        return client_options

    def map_client_options(self, options: dict[str, Any]) -> dict[str, Any]:
        """Map configuration options to PyMongo client options.

        Args:
            options: Configuration options

        Returns:
            Dict[str, Any]: PyMongo client options
        """
        return self._map_options(options)

    @property
    def backend(self) -> str:
        """Get backend name.

        Returns:
            str: Backend name
        """
        return "mongodb"

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._available) + len(self._in_use)

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return len(self._available)

    @property
    def in_use(self) -> int:
        """Get number of connections in use."""
        return len(self._in_use)

    async def init(self) -> None:
        """Initialize pool.

        This method creates the initial connections.

        Raises:
            ConnectionError: If pool initialization fails
            TimeoutError: If connection timeout occurs
            Exception: For other initialization errors
        """
        async with self._lock:
            try:
                logger.info(
                    "Initializing MongoDB pool with URI: %s, database: %s",
                    self._uri,
                    self._database,
                )

                # Map options to PyMongo format
                client_options = self._map_options(self._kwargs.get("options", {}))
                logger.debug("Using client options: %s", client_options)

                # Create client with mapped options and retry logic
                max_retries = 3
                retry_delay = 1.0  # seconds

                for attempt in range(max_retries):
                    try:
                        self._client = AsyncIOMotorClient(
                            self._uri,
                            minPoolSize=self._min_size,
                            maxPoolSize=self._max_size,
                            **client_options,
                        )

                        # Test connection
                        await self._client.admin.command("ping")
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise MongoDBConnectionError(
                                f"Failed to connect to MongoDB after {max_retries} attempts: {e}"
                            ) from e
                        logger.warning(
                            "Connection attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                            attempt + 1,
                            max_retries,
                            str(e),
                            retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

                # Create initial connections
                connection_errors: list[str] = []
                for i in range(self._min_size):
                    try:
                        conn = self._create_connection()
                        await conn.ping()  # Verify connection works
                        self._available.add(conn)
                        logger.debug("Created connection %d/%d", i + 1, self._min_size)
                    except Exception as e:
                        connection_errors.append(str(e))

                if connection_errors:
                    raise MongoDBConnectionError(
                        f"Failed to create some initial connections: {'; '.join(connection_errors)}"
                    )

                logger.info(
                    "Successfully initialized MongoDB pool with %d connections",
                    self.size,
                )
            except Exception as e:
                logger.error("Failed to initialize MongoDB pool: %s", str(e))
                if self._client:
                    self._client.close()
                    self._client = None
                raise

    def _create_connection(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Create new connection.

        Returns:
            AsyncConnectionProtocol[DB, COLL]: New connection

        Raises:
            MongoDBConnectionError: If connection creation fails
        """
        if not self._client:
            raise MongoDBConnectionError("Client not initialized")

        try:
            # Create connection
            return cast(
                AsyncConnectionProtocol[DB, COLL],
                MongoConnection(
                    client=self._client,
                    database=self._database,
                    collection="",  # Empty string as default collection
                    retry_policy=self._retry_policy,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
        except Exception as e:
            logger.error("Failed to create MongoDB connection: %s", str(e))
            raise MongoDBConnectionError(
                f"Failed to create MongoDB connection: {e!s}",
            ) from e

    async def acquire(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Acquire connection from pool.

        Returns:
            AsyncConnectionProtocol: Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
            ConnectionError: If connection creation fails
        """
        async with self._lock:
            # Get available connection or create new one
            if not self._available and self.size < self.max_size:
                try:
                    conn = self._create_connection()
                    await conn.ping()  # Verify connection works
                    self._available.add(conn)
                    logger.debug("Created new connection, pool size: %d", self.size)
                except Exception as e:
                    logger.error("Failed to create new connection: %s", str(e))
                    raise MongoDBConnectionError(
                        f"Failed to create connection: {e!s}",
                    ) from e

            # Check if pool is exhausted
            if not self._available:
                logger.warning(
                    "Pool exhausted - Size: %d, In use: %d, Available: %d",
                    self.size,
                    self.in_use,
                    self.available,
                )
                raise PoolExhaustedError(
                    "Connection pool exhausted",
                    backend=self.backend,
                    pool_size=self.max_size,
                    active_connections=len(self._in_use),
                    waiting_requests=0,
                )

            # Get connection from available set
            conn = self._available.pop()
            self._in_use.add(conn)
            logger.debug(
                "Acquired connection - Pool size: %d, In use: %d, Available: %d",
                self.size,
                self.in_use,
                self.available,
            )

            return conn

    async def release(self, conn: AsyncConnectionProtocol[DB, COLL]) -> None:
        """Release connection back to pool.

        Args:
            conn: Connection to release
        """
        async with self._lock:
            try:
                # Move connection back to available set
                self._in_use.remove(conn)
                try:
                    if await conn.ping():
                        self._available.add(conn)
                        logger.debug(
                            "Released healthy connection - Pool size: %d, In use: %d, Available: %d",
                            self.size,
                            self.in_use,
                            self.available,
                        )
                    else:
                        logger.warning("Connection ping failed, closing connection")
                        await conn.close()
                except Exception as e:
                    logger.warning("Connection health check failed: %s", str(e))
                    await conn.close()
            except ValueError:
                logger.warning("Attempted to release connection not in pool")
                pass

    async def connection(
        self,
    ) -> AsyncContextManager[AsyncConnectionProtocol[DB, COLL]]:
        """Get connection from pool.

        Returns:
            Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
            ConnectionError: If connection creation fails
        """
        return _ConnectionManager(self)

    async def close(self) -> None:
        """Close pool and cleanup resources."""
        await self.destroy()

    async def destroy(self) -> None:
        """Destroy pool and all connections."""
        if self._client:
            try:
                # Clear connections
                await self.clear()

                # Close client
                self._client.close()
                self._client = None

                logger.info("Destroyed MongoDB pool")
            except Exception as e:
                logger.error("Error destroying MongoDB pool: %s", str(e))
                raise

    async def clear(self) -> None:
        """Clear all connections."""
        async with self._lock:
            try:
                # Close all connections
                for conn in self._available | self._in_use:
                    try:
                        await conn.close()
                    except Exception as e:
                        logger.warning("Error closing connection: %s", str(e))

                # Clear sets
                self._available.clear()
                self._in_use.clear()

                logger.info("Cleared all connections from pool")
            except Exception as e:
                logger.error("Error clearing connections: %s", str(e))
                raise

    async def health_check(self) -> bool:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        if not self._client:
            logger.warning("Health check failed: Client not initialized")
            return False

        try:
            await self._client.admin.command("ping")
            logger.debug("Health check passed")
            return True
        except Exception as e:
            logger.warning("Health check failed: %s", str(e))
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "database": self._database,
            "size": self.size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": self.available,
            "in_use": self.in_use,
        }

    @property
    def database_name(self) -> str:
        """Get database name."""
        return self._database
