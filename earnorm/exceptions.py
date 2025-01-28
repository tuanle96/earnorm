"""EarnORM exceptions.

This module contains all custom exceptions used in EarnORM.
"""

from typing import Any, Dict, Optional


class EarnORMError(Exception):
    """Base class for all EarnORM exceptions."""

    def __init__(self, message: str) -> None:
        """Initialize exception.

        Args:
            message: Error message
        """
        super().__init__(message)
        self.message = message


# Config-related exceptions
class ConfigError(EarnORMError):
    """Raised when there is an error in configuration."""

    def __init__(self, message: str) -> None:
        """Initialize exception.

        Args:
            message: Error message
        """
        super().__init__(f"Configuration error: {message}")


class ConfigValidationError(ConfigError):
    """Error raised when config validation fails.

    This error is raised when configuration validation fails,
    typically when required fields are missing or have invalid values.
    """

    def __init__(self, message: str) -> None:
        """Initialize config validation error.

        Args:
            message: Error message
        """
        super().__init__(f"Validation error: {message}")


class ConfigMigrationError(ConfigError):
    """Error raised when config migration fails.

    This error is raised when configuration migration between versions fails,
    typically when there are incompatible changes or data corruption.
    """

    def __init__(self, message: str) -> None:
        """Initialize config migration error.

        Args:
            message: Error message
        """
        super().__init__(f"Migration error: {message}")


class ConfigBackupError(ConfigError):
    """Error raised when config backup/restore fails.

    This error is raised when configuration backup or restore operations fail,
    typically due to file system issues or data corruption.
    """

    def __init__(self, message: str) -> None:
        """Initialize config backup error.

        Args:
            message: Error message
        """
        super().__init__(f"Backup error: {message}")


class ValidationError(EarnORMError):
    """Error raised when validation fails.

    This error is raised when model validation fails,
    typically when custom validation rules are not satisfied.

    Attributes:
        message: Error message
        code: Error code for identifying validation error type
    """

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            code: Error code for identifying validation error type
        """
        self.code = code or "validation_error"
        super().__init__(f"{message} (code={self.code})")


class UniqueConstraintError(ValidationError):
    """Error raised when unique constraint is violated.

    This error is raised when a unique constraint is violated,
    typically when trying to create or update a record with
    a value that already exists in a unique field.

    Attributes:
        message: Error message
        field_name: Name of field that caused the error
        value: Value that violated the constraint
        code: Error code for identifying validation error type
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str,
        value: Any,
        code: Optional[str] = None,
    ) -> None:
        """Initialize unique constraint error.

        Args:
            message: Error message
            field_name: Field name
            value: Value that violated the constraint
            code: Error code for identifying validation error type
        """
        self.field_name = field_name
        self.value = value
        super().__init__(
            f"{field_name}: {message} (value={value})",
            code=code or "unique_constraint_error",
        )


# Field-related exceptions
class FieldError(EarnORMError):
    """Base class for field-related errors.

    Attributes:
        message: Error message
        field_name: Name of field that caused the error
        code: Error code for identifying error type
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str,
        code: Optional[str] = None,
    ) -> None:
        """Initialize field error.

        Args:
            message: Error message
            field_name: Field name
            code: Error code for identifying error type
        """
        self.field_name = field_name
        self.code = code or "field_error"
        super().__init__(f"{field_name}: {message} (code={self.code})")


class FieldValidationError(FieldError):
    """Error raised when field validation fails.

    This error is raised when a field value fails validation,
    either due to type mismatch, constraint violation, or
    custom validation rules.
    """

    def __init__(
        self,
        message: str,
        *,
        field_name: str,
        code: Optional[str] = "validation_error",
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Field name
            code: Error code for identifying validation error type
        """
        super().__init__(message, field_name=field_name, code=code)


class ModelResolutionError(FieldError):
    """Error raised when model resolution fails.

    This error is raised when a model class cannot be resolved,
    typically when trying to resolve a model name to its class
    without having access to the model registry.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize model resolution error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="model_resolution_error")


class ModelNotFoundError(FieldError):
    """Error raised when model is not found.

    This error is raised when a model class cannot be found
    in the model registry, typically when trying to resolve
    a model name that doesn't exist.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize model not found error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="model_not_found_error")


# Database-related exceptions
class DatabaseError(EarnORMError):
    """Base class for database-related errors."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize database error.

        Args:
            message: Error message
            backend: Database backend name
        """
        self.backend = backend
        super().__init__(f"{backend}: {message}")


class DatabaseConnectionError(DatabaseError):
    """Error raised when database connection fails."""

    ...


class MongoDBConnectionError(DatabaseError):
    """Error raised when MongoDB connection fails."""

    def __init__(self, message: str) -> None:
        """Initialize connection error.

        Args:
            message: Error message
        """
        super().__init__(message, backend="mongodb")


class RedisConnectionError(DatabaseError):
    """Error raised when Redis connection fails."""

    def __init__(self, message: str) -> None:
        """Initialize connection error.

        Args:
            message: Error message
        """
        super().__init__(message, backend="redis")


class MySQLConnectionError(DatabaseError):
    """Error raised when MySQL connection fails."""

    def __init__(self, message: str) -> None:
        """Initialize connection error.

        Args:
            message: Error message
        """
        super().__init__(message, backend="mysql")


class PostgreSQLConnectionError(DatabaseError):
    """Error raised when PostgreSQL connection fails."""

    def __init__(self, message: str) -> None:
        """Initialize connection error.

        Args:
            message: Error message
        """
        super().__init__(message, backend="postgresql")


class QueryError(DatabaseError):
    """Error raised when database query fails."""

    def __init__(self, message: str, *, backend: str, query: str) -> None:
        """Initialize query error.

        Args:
            message: Error message
            backend: Database backend name
            query: Failed query
        """
        self.query = query
        super().__init__(f"{message} (query={query})", backend=backend)


class PoolError(DatabaseError):
    """Base class for pool-related errors."""

    def __init__(
        self, message: str, *, backend: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize pool error.

        Args:
            message: Error message
            backend: Database backend name
            context: Additional context information
        """
        self.context = context or {}
        super().__init__(message, backend=backend)


class PoolExhaustedError(PoolError):
    """Error raised when connection pool is exhausted."""

    def __init__(
        self,
        message: str,
        *,
        backend: str,
        pool_size: int,
        active_connections: int,
        waiting_requests: int,
    ) -> None:
        """Initialize pool exhausted error.

        Args:
            message: Error message
            backend: Database backend name
            pool_size: Maximum pool size
            active_connections: Number of active connections
            waiting_requests: Number of waiting requests
        """
        context = {
            "pool_size": pool_size,
            "active_connections": active_connections,
            "waiting_requests": waiting_requests,
        }
        super().__init__(message, backend=backend, context=context)


class CircuitBreakerError(PoolError):
    """Error raised when circuit breaker is open."""

    def __init__(
        self,
        message: str,
        *,
        backend: str,
        failures: int,
        last_failure_time: float,
        reset_time: float,
    ) -> None:
        """Initialize circuit breaker error.

        Args:
            message: Error message
            backend: Database backend name
            failures: Number of consecutive failures
            last_failure_time: Timestamp of last failure
            reset_time: Timestamp when circuit will reset
        """
        context = {
            "failures": failures,
            "last_failure_time": last_failure_time,
            "reset_time": reset_time,
        }
        super().__init__(message, backend=backend, context=context)


class RetryError(PoolError):
    """Error raised when all retry attempts fail."""

    def __init__(
        self,
        message: str,
        *,
        backend: str,
        attempts: int,
        elapsed: float,
        last_error: Optional[Exception] = None,
    ) -> None:
        """Initialize retry error.

        Args:
            message: Error message
            backend: Database backend name
            attempts: Number of retry attempts
            elapsed: Total elapsed time
            last_error: Last error that occurred
        """
        context = {
            "attempts": attempts,
            "elapsed": elapsed,
            "last_error": str(last_error) if last_error else None,
        }
        super().__init__(message, backend=backend, context=context)


# Cache-related exceptions
class CacheError(EarnORMError):
    """Base class for cache-related errors."""

    def __init__(self, message: str, *, backend: str) -> None:
        """Initialize cache error.

        Args:
            message: Error message
            backend: Cache backend name
        """
        self.backend = backend
        super().__init__(f"{backend}: {message}")


class CacheConnectionError(CacheError):
    """Error raised when cache connection fails."""

    ...


class CacheKeyError(CacheError):
    """Error raised when cache key operation fails."""

    def __init__(self, message: str, *, backend: str, key: str) -> None:
        """Initialize cache key error.

        Args:
            message: Error message
            backend: Cache backend name
            key: Failed key
        """
        self.key = key
        super().__init__(f"{message} (key={key})", backend=backend)


# Dependency Injection related exceptions
class DIError(EarnORMError):
    """Base class for all DI exceptions.

    This error is raised when there are issues with:
    - Service registration
    - Service resolution
    - Circular dependencies
    - Missing dependencies
    - Event handling
    """

    def __init__(self, message: str) -> None:
        """Initialize DI error.

        Args:
            message: Error message describing the DI issue
        """
        super().__init__(f"DI error: {message}")


class CircularDependencyError(DIError):
    """Error raised when circular dependency is detected.

    This error is raised when a circular dependency is detected
    in the dependency graph during service resolution.
    """

    def __init__(self, message: str) -> None:
        """Initialize circular dependency error.

        Args:
            message: Error message describing the circular dependency
        """
        super().__init__(f"Circular dependency detected: {message}")


class EventError(DIError):
    """Error raised when event handling fails.

    This error is raised when there are issues with:
    - Event registration
    - Event emission
    - Event handler execution
    """

    def __init__(self, message: str) -> None:
        """Initialize event error.

        Args:
            message: Error message describing the event error
        """
        super().__init__(f"Event error: {message}")


class ServiceNotFoundError(DIError):
    """Error raised when service is not found.

    This error is raised when trying to get a service that:
    - Is not registered
    - Has been unregistered
    - Cannot be created by any factory
    """

    def __init__(self, name: str) -> None:
        """Initialize service not found error.

        Args:
            name: Name of the service that was not found
        """
        super().__init__(f"Service not found: {name}")


class ServiceInitializationError(DIError):
    """Error raised when service initialization fails.

    This error is raised when:
    - Service constructor fails
    - Service async initialization fails
    - Service dependencies cannot be resolved
    """

    def __init__(self, name: str, message: str) -> None:
        """Initialize service initialization error.

        Args:
            name: Name of the service that failed to initialize
            message: Error message describing the initialization error
        """
        super().__init__(f"Failed to initialize service {name}: {message}")


class FactoryError(DIError):
    """Error raised when factory operation fails.

    This error is raised when:
    - Factory registration fails
    - Factory creation fails
    - Factory dependencies cannot be resolved
    """

    def __init__(self, name: str, message: str) -> None:
        """Initialize factory error.

        Args:
            name: Name of the factory that failed
            message: Error message describing the factory error
        """
        super().__init__(f"Factory error for {name}: {message}")


class RegistrationError(EarnORMError):
    """Error raised when service registration fails.

    This error is raised when there are issues with:
    - Service registration in DI container
    - Model registration in registry
    - Event handler registration
    - Connection pool registration
    """

    def __init__(self, message: str) -> None:
        """Initialize registration error.

        Args:
            message: Error message describing the registration issue
        """
        super().__init__(f"Registration error: {message}")


class CleanupError(EarnORMError):
    """Error raised when cleanup process fails.

    This error is raised when there are issues with:
    - Resource cleanup
    - Connection pool shutdown
    - Event handler cleanup
    - Cache invalidation
    """

    def __init__(self, message: str) -> None:
        """Initialize cleanup error.

        Args:
            message: Error message describing the cleanup issue
        """
        super().__init__(f"Cleanup error: {message}")


class InitializationError(EarnORMError):
    """Error raised when initialization fails.

    This error is raised when there are issues with:
    - Framework initialization
    - Service initialization
    - Connection pool initialization
    - Cache initialization
    """

    def __init__(self, message: str) -> None:
        """Initialize initialization error.

        Args:
            message: Error message describing the initialization issue
        """
        super().__init__(f"Initialization error: {message}")
