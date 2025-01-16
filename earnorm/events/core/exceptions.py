"""Event exceptions implementation.

This module provides exceptions for the event system.
It includes exceptions for event handling, validation, and serialization.

Features:
- Base event exception
- Handler exceptions
- Validation exceptions
- Serialization exceptions
- Connection exceptions
- Publishing exceptions

Examples:
    ```python
    from earnorm.events.core.exceptions import (
        EventError,
        HandlerError,
        ValidationError,
        SerializationError,
    )

    try:
        # Handle event
        await handler.handle(event)
    except HandlerError as e:
        logger.error("Failed to handle event: %s", str(e))

    try:
        # Validate event
        validate_event(event)
    except ValidationError as e:
        logger.error("Invalid event: %s", str(e))
    ```
"""


class EventError(Exception):
    """Base exception for event errors.

    This is the base class for all event-related exceptions.
    All other event exceptions inherit from this class.

    Attributes:
        message: Error message describing the failure

    Examples:
        ```python
        try:
            # Event operation
            process_event(event)
        except EventError as e:
            logger.error("Event error: %s", str(e))
        ```
    """

    def __init__(self, message: str) -> None:
        """Initialize exception.

        Args:
            message: Error message describing the failure
        """
        super().__init__(message)
        self.message = message


class HandlerError(EventError):
    """Exception for event handler errors.

    This exception is raised when an event handler fails.
    It includes details about the handler and event.

    Attributes:
        message: Error message describing the handler failure
        handler_id: Optional ID of the failed handler
        event_name: Optional name of the event being handled

    Examples:
        ```python
        try:
            # Handle event
            await handler.handle(event)
        except HandlerError as e:
            logger.error("Handler failed: %s", str(e))
        ```
    """

    pass


class ValidationError(EventError):
    """Exception for event validation errors.

    This exception is raised when event validation fails.
    It includes details about the validation failure.

    Attributes:
        message: Error message describing the validation failure
        field: Optional name of the invalid field
        value: Optional invalid value

    Examples:
        ```python
        try:
            # Validate event
            validate_event(event)
        except ValidationError as e:
            logger.error("Invalid event: %s", str(e))
        ```
    """

    pass


class SerializationError(EventError):
    """Exception for event serialization errors.

    This exception is raised when event serialization fails.
    It includes details about the serialization failure.

    Attributes:
        message: Error message describing the serialization failure
        data: Optional data that failed to serialize

    Examples:
        ```python
        try:
            # Serialize event
            json_str = serializer.serialize(event)
        except SerializationError as e:
            logger.error("Failed to serialize event: %s", str(e))
        ```
    """

    pass


class ConnectionError(EventError):
    """Exception for event backend connection errors.

    This exception is raised when connecting to a backend fails.
    It includes details about the connection failure.

    Attributes:
        message: Error message describing the connection failure
        backend: Optional name of the failed backend
        uri: Optional connection URI

    Examples:
        ```python
        try:
            # Connect to backend
            await backend.connect()
        except ConnectionError as e:
            logger.error("Failed to connect: %s", str(e))
        ```
    """

    pass


class PublishError(EventError):
    """Exception for event publishing errors.

    This exception is raised when publishing an event fails.
    It includes details about the publish failure.

    Attributes:
        message: Error message describing the publish failure
        event_name: Optional name of the event that failed to publish
        backend: Optional name of the failed backend

    Examples:
        ```python
        try:
            # Publish event
            await backend.publish(event)
        except PublishError as e:
            logger.error("Failed to publish event: %s", str(e))
        ```
    """

    pass
