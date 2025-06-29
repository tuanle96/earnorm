"""EarnORM exceptions.

This module contains all custom exceptions used in EarnORM.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


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


@dataclass
class ValidationError(BaseException):
    """Structured validation error with context.

    This class provides detailed error information including:
    - Error message
    - Field name
    - Error code
    - Validation context
    - Parent/child errors for nested validation

    Attributes:
        message: Error message
        field_name: Name of field that failed validation
        code: Error code for programmatic handling
        context: Optional validation context
        parent: Optional parent error for nested validation
        children: List of child errors
    """

    message: str
    field_name: str
    code: str
    context: dict[str, Any] | None = None
    parent: Optional["ValidationError"] = None
    children: list["ValidationError"] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_child(self, error: "ValidationError") -> None:
        """Add child error.

        Args:
            error: Child validation error
        """
        self.children.append(error)
        error.parent = self

    def get_error_tree(self) -> dict[str, Any]:
        """Get hierarchical error structure.

        Returns:
            Dict containing error information and child errors
        """
        result = {
            "message": self.message,
            "field": self.field_name,
            "code": self.code,
            "timestamp": self.timestamp,
        }

        if self.context:
            result["context"] = self.context  # type: ignore

        if self.children:
            result["children"] = [child.get_error_tree() for child in self.children]  # type: ignore

        return result


class FieldValidationError(Exception):
    """Exception for field validation errors.

    This exception wraps ValidationError to provide structured error handling.

    Attributes:
        error: Underlying ValidationError instance
    """

    def __init__(
        self,
        message: str,
        field_name: str,
        code: str,
        context: dict[str, Any] | None = None,
        parent: ValidationError | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field_name: Name of field that failed validation
            code: Error code
            context: Optional validation context
            parent: Optional parent error
        """
        super().__init__(message)
        self.error = ValidationError(
            message=message,
            field_name=field_name,
            code=code,
            context=context,
            parent=parent,
        )

    def add_child(self, error: ValidationError) -> None:
        """Add child error.

        Args:
            error: Child validation error
        """
        self.error.add_child(error)

    def get_error_tree(self) -> dict[str, Any]:
        """Get hierarchical error structure.

        Returns:
            Dict containing error information and child errors
        """
        return self.error.get_error_tree()


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
        code: str | None = None,
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
            field_name=field_name,
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
        code: str | None = None,
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


class RelationModelResolutionError(FieldError):
    """Error raised when relation model resolution fails.

    This error is raised when a relation field cannot resolve its referenced model,
    typically when the model name is invalid or the model is not registered.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize relation model resolution error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="relation_model_resolution_error")


class RelationBackReferenceError(FieldError):
    """Error raised when relation back reference setup fails.

    This error is raised when a relation field cannot set up its back reference,
    typically when the back reference field does not exist on the related model.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize relation back reference error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="relation_back_reference_error")


class RelationLoadError(FieldError):
    """Error raised when loading related records fails.

    This error is raised when a relation field cannot load its related records,
    typically due to database errors or invalid record IDs.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize relation load error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="relation_load_error")


class RelationConstraintError(FieldError):
    """Error raised when relation constraints are violated.

    This error is raised when relation constraints are violated,
    typically when trying to delete records that are still referenced
    by other records through relation fields.
    """

    def __init__(self, message: str, *, field_name: str) -> None:
        """Initialize relation constraint error.

        Args:
            message: Error message
            field_name: Field name
        """
        super().__init__(message, field_name=field_name, code="relation_constraint_error")


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

    def __init__(self, message: str, *, backend: str, context: dict[str, Any] | None = None) -> None:
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
        last_error: Exception | None = None,
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


class SerializationError(EarnORMError):
    """Error raised when serialization fails."""

    def __init__(self, message: str, *, backend: str, original_error: Exception | None = None) -> None:
        """Initialize serialization error.

        Args:
            message: Error message describing the serialization issue
            backend: Serialization backend name
            original_error: Original exception that caused this error
        """
        self.backend = backend
        self.original_error = original_error
        super().__init__(f"{backend}: {message}")


class CacheError(EarnORMError):
    """Raised when a cache operation fails."""

    pass


class DeletedRecordError(EarnORMError):
    """Error raised when attempting to access a deleted record.

    This error is raised when trying to access attributes or perform operations
    on a record that has been deleted from the database.

    Examples:
        >>> user = await User.browse("123")
        >>> await user.unlink()  # Delete the record
        >>> try:
        ...     name = await user.name  # Raises DeletedRecordError
        ... except DeletedRecordError as e:
        ...     print(f"Cannot access deleted record: {e}")
    """

    def __init__(self, model_name: str) -> None:
        """Initialize deleted record error.

        Args:
            model_name: Name of the model that was deleted
        """
        super().__init__(f"Cannot access attributes of deleted {model_name} record")
        self.model_name = model_name
