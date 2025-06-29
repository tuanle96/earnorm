"""Decorators for database operations.

This module provides decorators to enhance database operations with retry
and circuit breaker functionality.

Examples:
    ```python
    from earnorm.pool.decorators import with_resilience
    from earnorm.pool.retry import RetryPolicy
    from earnorm.pool.circuit import CircuitBreaker

    # Use both retry and circuit breaker
    @with_resilience(
        retry_policy=RetryPolicy(max_retries=3),
        circuit_breaker=CircuitBreaker(failure_threshold=5),
        backend="mongodb",
    )
    async def find_user(user_id: str) -> Dict[str, Any]:
        return await db.users.find_one({"_id": user_id})

    # Use only retry
    @with_resilience(retry_policy=RetryPolicy(max_retries=3), backend="mongodb")
    async def create_user(user: Dict[str, Any]) -> str:
        result = await db.users.insert_one(user)
        return str(result.inserted_id)

    # Use only circuit breaker
    @with_resilience(circuit_breaker=CircuitBreaker(failure_threshold=5), backend="mongodb")
    async def update_user(user_id: str, update: Dict[str, Any]) -> bool:
        result = await db.users.update_one(
            {"_id": user_id},
            {"$set": update}
        )
        return result.modified_count > 0
    ```
"""

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, overload

from earnorm.exceptions import CircuitBreakerError, RetryError

from .circuit import CircuitBreaker
from .retry import RetryContext, RetryPolicy

# Configure logger
logger = logging.getLogger(__name__)

# Type variable for the return type of the decorated function
T = TypeVar("T")

# Type alias for async functions
AsyncFunc = Callable[..., Awaitable[T]]


class ResilienceError(Exception):
    """Base class for resilience-related errors."""

    def __init__(self, message: str, context: Any = None) -> None:
        """Initialize error.

        Args:
            message: Error message
            context: Additional context
        """
        super().__init__(message)
        self.context = context


class InvalidConfigurationError(ResilienceError):
    """Error raised when resilience configuration is invalid."""

    pass


def validate_retry_policy(policy: RetryPolicy) -> None:
    """Validate retry policy configuration.

    Args:
        policy: Retry policy to validate

    Raises:
        InvalidConfigurationError: If policy configuration is invalid
    """
    if policy.max_retries < 0:
        raise InvalidConfigurationError("max_retries must be >= 0", {"max_retries": policy.max_retries})
    if policy.base_delay < 0:
        raise InvalidConfigurationError("base_delay must be >= 0", {"base_delay": policy.base_delay})
    if policy.max_delay < policy.base_delay:
        raise InvalidConfigurationError(
            "max_delay must be >= base_delay",
            {"max_delay": policy.max_delay, "base_delay": policy.base_delay},
        )


def validate_circuit_breaker(breaker: CircuitBreaker) -> None:
    """Validate circuit breaker configuration.

    Args:
        breaker: Circuit breaker to validate

    Raises:
        InvalidConfigurationError: If breaker configuration is invalid
    """
    # Get configuration as dict
    config = {
        "failure_threshold": getattr(breaker, "_failure_threshold", 5),
        "reset_timeout": getattr(breaker, "_reset_timeout", 60.0),
        "half_open_timeout": getattr(breaker, "_half_open_timeout", 30.0),
    }

    if config["failure_threshold"] < 1:
        raise InvalidConfigurationError(
            "failure_threshold must be >= 1",
            {"failure_threshold": config["failure_threshold"]},
        )
    if config["reset_timeout"] < 0:
        raise InvalidConfigurationError("reset_timeout must be >= 0", {"reset_timeout": config["reset_timeout"]})
    if config["half_open_timeout"] < 0:
        raise InvalidConfigurationError(
            "half_open_timeout must be >= 0",
            {"half_open_timeout": config["half_open_timeout"]},
        )


@overload
def with_resilience(
    func: AsyncFunc[T],
) -> AsyncFunc[T]: ...


@overload
def with_resilience(
    *,
    retry_policy: RetryPolicy | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    backend: str = "unknown",
) -> Callable[[AsyncFunc[T]], AsyncFunc[T]]: ...


def with_resilience(
    func: AsyncFunc[T] | None = None,
    *,
    retry_policy: RetryPolicy | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    backend: str = "unknown",
) -> AsyncFunc[T] | Callable[[AsyncFunc[T]], AsyncFunc[T]]:
    """Decorator to add retry and circuit breaker functionality to async database operations.

    This decorator can:
    1. Automatically retry failed operations using exponential backoff
    2. Prevent cascade failures using circuit breaker pattern
    3. Combine both retry and circuit breaker patterns

    Args:
        func: The async function to decorate
        retry_policy: Configuration for retry mechanism
        circuit_breaker: Configuration for circuit breaker
        backend: Database backend name

    Returns:
        Decorated async function with retry and/or circuit breaker functionality

    Examples:
        >>> @with_resilience
        ... async def database_operation() -> Dict[str, Any]:
        ...     return await collection.find_one({"status": "active"})

        >>> @with_resilience(
        ...     retry_policy=RetryPolicy(max_retries=3),
        ...     circuit_breaker=CircuitBreaker(failure_threshold=5),
        ...     backend="mongodb",
        ... )
        ... async def database_operation() -> Dict[str, Any]:
        ...     return await collection.find_one({"status": "active"})
    """
    if func is None:
        return lambda f: _with_resilience(f, retry_policy, circuit_breaker, backend)
    return _with_resilience(func, retry_policy, circuit_breaker, backend)


def _with_resilience(
    func: AsyncFunc[T],
    retry_policy: RetryPolicy | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    backend: str = "unknown",
) -> AsyncFunc[T]:
    """Internal implementation of with_resilience decorator."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        operation_name = f"{func.__module__}.{func.__qualname__}"
        logger.debug(
            "Executing operation %s with resilience (retry=%s, circuit_breaker=%s, backend=%s)",
            operation_name,
            bool(retry_policy),
            bool(circuit_breaker),
            backend,
        )

        # Create retry context if policy provided
        retry_ctx = RetryContext(retry_policy, backend=backend) if retry_policy else None

        # Create circuit breaker context if provided
        circuit_ctx = circuit_breaker if circuit_breaker else None
        if circuit_ctx:
            circuit_ctx._backend = backend  # type: ignore

        # Combine retry and circuit breaker
        async def execute_with_resilience() -> T:
            """Execute the wrapped function with retry and circuit breaker.

            Returns:
                Result from the wrapped function

            Raises:
                RetryError: If all retry attempts fail
                CircuitBreakerError: If circuit breaker is open
                Exception: Any exception from the wrapped function
            """
            if circuit_ctx:
                return await circuit_ctx.execute(func, *args, **kwargs)
            return await func(*args, **kwargs)

        try:
            if retry_ctx:
                result = await retry_ctx.execute(execute_with_resilience)
            else:
                result = await execute_with_resilience()

            logger.debug(
                "Operation %s completed successfully",
                operation_name,
            )
            return result

        except (RetryError, CircuitBreakerError) as e:
            logger.error(
                "Operation %s failed with resilience error: %s",
                operation_name,
                str(e),
                exc_info=True,
                extra={"error_context": getattr(e, "context", {})},
            )
            raise

        except Exception as e:
            logger.error(
                "Operation %s failed with unexpected error: %s",
                operation_name,
                str(e),
                exc_info=True,
            )
            raise

    return wrapper
