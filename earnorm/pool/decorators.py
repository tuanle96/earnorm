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
    )
    async def find_user(user_id: str) -> Dict[str, Any]:
        return await db.users.find_one({"_id": user_id})

    # Use only retry
    @with_resilience(retry_policy=RetryPolicy(max_retries=3))
    async def create_user(user: Dict[str, Any]) -> str:
        result = await db.users.insert_one(user)
        return str(result.inserted_id)

    # Use only circuit breaker
    @with_resilience(circuit_breaker=CircuitBreaker(failure_threshold=5))
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
from typing import Any, Awaitable, Callable, Optional, TypeVar

from earnorm.pool.circuit import CircuitBreaker, CircuitBreakerError
from earnorm.pool.retry import RetryContext, RetryError, RetryPolicy

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
        raise InvalidConfigurationError(
            "max_retries must be >= 0", {"max_retries": policy.max_retries}
        )
    if policy.base_delay < 0:
        raise InvalidConfigurationError(
            "base_delay must be >= 0", {"base_delay": policy.base_delay}
        )
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
        raise InvalidConfigurationError(
            "reset_timeout must be >= 0", {"reset_timeout": config["reset_timeout"]}
        )
    if config["half_open_timeout"] < 0:
        raise InvalidConfigurationError(
            "half_open_timeout must be >= 0",
            {"half_open_timeout": config["half_open_timeout"]},
        )


def with_resilience(
    retry_policy: Optional[RetryPolicy] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
) -> Callable[[AsyncFunc[T]], AsyncFunc[T]]:
    """Decorator to add retry and circuit breaker functionality to async database operations.

    This decorator can:
    1. Automatically retry failed operations using exponential backoff
    2. Prevent cascade failures using circuit breaker pattern
    3. Combine both retry and circuit breaker patterns

    Args:
        retry_policy: Configuration for retry mechanism. If None, no retry will be performed.
        circuit_breaker: Configuration for circuit breaker. If None, no circuit breaking will be used.

    Returns:
        Decorated async function with retry and/or circuit breaker functionality.

    Raises:
        RetryError: If all retry attempts fail
        CircuitBreakerError: If circuit breaker is open
        ValueError: If both retry_policy and circuit_breaker are None

    Examples:
        ```python
        # Configure retry and circuit breaker
        retry = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=0.1
        )
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_timeout=30.0
        )

        # Apply decorator
        @with_resilience(retry_policy=retry, circuit_breaker=breaker)
        async def database_operation() -> Dict[str, Any]:
            return await collection.find_one({"status": "active"})

        # Use decorated function
        try:
            result = await database_operation()
        except RetryError as e:
            print(f"Operation failed after {e.attempts} retries")
        except CircuitBreakerError as e:
            print(f"Circuit breaker is {e.state}")
        ```
    """
    # Validate configuration
    if retry_policy is None and circuit_breaker is None:
        raise InvalidConfigurationError(
            "At least one of retry_policy or circuit_breaker must be provided"
        )

    if retry_policy:
        validate_retry_policy(retry_policy)
    if circuit_breaker:
        validate_circuit_breaker(circuit_breaker)

    def decorator(func: AsyncFunc[T]) -> AsyncFunc[T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            operation_name = f"{func.__module__}.{func.__qualname__}"
            logger.debug(
                "Executing operation %s with resilience (retry=%s, circuit_breaker=%s)",
                operation_name,
                bool(retry_policy),
                bool(circuit_breaker),
            )

            # Create retry context if policy provided
            retry_ctx = RetryContext(retry_policy) if retry_policy else None

            # Create circuit breaker context if provided
            circuit_ctx = circuit_breaker if circuit_breaker else None

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

            except RetryError as e:
                # Add context to retry error
                context = getattr(e, "context", {})
                attempts = context.get("attempts", 0)
                elapsed = context.get("elapsed", 0.0)
                error_msg = (
                    f"Operation {operation_name} failed after {attempts} retries"
                )
                error_context = {
                    "attempts": attempts,
                    "elapsed": elapsed,
                    "args": args,
                    "kwargs": kwargs,
                }
                logger.error(
                    error_msg,
                    extra={"error_context": error_context},
                    exc_info=True,
                )
                raise RetryError(error_msg, error_context) from e

            except CircuitBreakerError as e:
                # Add context to circuit breaker error
                context = getattr(e, "context", {})
                state = context.get("state", "unknown")
                failures = context.get("failures", 0)
                error_msg = f"Circuit breaker for {operation_name} is {state}"
                error_context = {
                    "state": state,
                    "failures": failures,
                    "args": args,
                    "kwargs": kwargs,
                }
                logger.error(
                    error_msg,
                    extra={"error_context": error_context},
                    exc_info=True,
                )
                raise CircuitBreakerError(error_msg, error_context) from e

            except Exception as e:
                # Log unexpected errors
                logger.error(
                    "Unexpected error in operation %s: %s",
                    operation_name,
                    str(e),
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator
