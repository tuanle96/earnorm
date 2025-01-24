"""Field event handlers implementation.

This module provides common event handlers for field events.
It supports:
- Logging handlers
- Validation handlers
- Change tracking handlers
- Error handling and retry
- Cleanup handlers
- Integration with core handlers

Examples:
    >>> bus = EventBus()
    >>> bus.subscribe(EventType.CHANGE, log_changes)
    >>> bus.subscribe(EventType.ERROR, handle_errors)
    >>> bus.subscribe(EventType.CLEANUP, cleanup_resources)
"""

import logging
from typing import Dict, List, Optional, Set, Union

from earnorm.fields.events.base import EventHandler, EventType, FieldEvent
from earnorm.fields.validators.base import ValidationError

# Set up logger
logger = logging.getLogger(__name__)


class FieldEventHandlerMixin:
    """Mixin for field event handlers.

    This mixin provides field-specific functionality for core handlers.
    """

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Handle field event.

        Override this method to implement field event handling.

        Args:
            event: Field event to handle
        """
        raise NotImplementedError


class LoggingHandler(FieldEventHandlerMixin):
    """Handler for logging field events."""

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Log field event based on type.

        Args:
            event: Field event to log
        """
        if event.type == EventType.CHANGE:
            logger.info(
                "Field %s changed from %r to %r",
                event.field.name,
                event.old_value,
                event.value,
            )
        elif event.type == EventType.ERROR:
            if event.error is not None:
                logger.error(
                    "Error in field %s: %s",
                    event.field.name,
                    str(event.error),
                    exc_info=event.error,
                )
        elif event.type == EventType.VALIDATE:
            logger.debug(
                "Validating field %s with value %r",
                event.field.name,
                event.value,
            )


class ChangeTracker(FieldEventHandlerMixin):
    """Handler for tracking field changes."""

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Track field changes in metadata.

        Args:
            event: Change event
        """
        if event.type != EventType.CHANGE:
            return

        changes: List[Dict[str, Union[str, object]]] = event.metadata.setdefault(
            "changes", []
        )
        changes.append(
            {
                "field": event.field.name,
                "old_value": event.old_value,
                "new_value": event.value,
                "timestamp": event.metadata.get("timestamp"),
            }
        )


class ValidationHandler(FieldEventHandlerMixin):
    """Handler for field validation with retry support."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Initialize validation handler.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._retry_count: Dict[str, int] = {}

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Validate field value.

        Args:
            event: Validation event

        Raises:
            ValidationError: If validation fails after retries
        """
        if event.type != EventType.VALIDATE:
            return

        field_id = f"{event.field.name}_{id(event.field)}"
        retry_count = self._retry_count.get(field_id, 0)

        try:
            # Validate required
            if event.field.required and event.value is None:  # type: ignore
                raise ValidationError(
                    message=f"Field {event.field.name} is required",
                    field_name=event.field.name,
                    code="required",
                )

            # Validate type
            if event.value is not None and not isinstance(
                event.value, event.field.value_type  # type: ignore
            ):
                raise ValidationError(
                    message=(
                        f"Field {event.field.name} expects {event.field.value_type.__name__}, "  # type: ignore
                        f"got {type(event.value).__name__}"
                    ),
                    field_name=event.field.name,
                    code="invalid_type",
                )

            # Reset retry count on success
            if field_id in self._retry_count:
                del self._retry_count[field_id]

        except ValidationError as error:
            if retry_count < self.max_retries:
                # Increment retry count
                self._retry_count[field_id] = retry_count + 1

                # Log retry attempt
                logger.warning(
                    "Validation failed for field %s, retrying (%d/%d): %s",
                    event.field.name,
                    retry_count + 1,
                    self.max_retries,
                    str(error),
                )

                # Add retry metadata to event
                event.metadata["retry_count"] = retry_count + 1
                event.metadata["max_retries"] = self.max_retries
                event.metadata["retry_delay"] = self.retry_delay
                event.metadata["original_error"] = error

                # Create validation error with retry info
                raise ValidationError(
                    message=f"Validation failed, retrying ({retry_count + 1}/{self.max_retries}): {str(error)}",
                    field_name=event.field.name,
                    code="validation_retry",
                )
            else:
                # Reset retry count on max retries
                if field_id in self._retry_count:
                    del self._retry_count[field_id]

                # Log final failure
                logger.error(
                    "Validation failed for field %s after %d retries: %s",
                    event.field.name,
                    self.max_retries,
                    str(error),
                )

                raise error


class CleanupHandler(FieldEventHandlerMixin):
    """Handler for cleaning up field resources."""

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Clean up field resources.

        Args:
            event: Cleanup event
        """
        if event.type != EventType.CLEANUP:
            return

        # Clean up any resources associated with field
        if hasattr(event.field, "cleanup"):
            await event.field.cleanup()  # type: ignore


class EventHandlerRegistry:
    """Registry for event handlers.

    This class manages both field handlers and core handlers.

    Attributes:
        _handlers: Dictionary mapping event types to sets of handlers
    """

    def __init__(self) -> None:
        """Initialize handler registry."""
        self._handlers: Dict[EventType, Set[EventHandler]] = {}

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        """Register event handler.

        Args:
            event_type: Type of event to handle
            handler: Event handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = set()
        self._handlers[event_type].add(handler)

    def unregister(self, event_type: EventType, handler: EventHandler) -> None:
        """Unregister event handler.

        Args:
            event_type: Type of event to unhandle
            handler: Event handler function
        """
        if event_type in self._handlers:
            self._handlers[event_type].discard(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]

    def get_handlers(self, event_type: Optional[EventType] = None) -> Set[EventHandler]:
        """Get event handlers.

        Args:
            event_type: Type of event to get handlers for, or None for all

        Returns:
            Set of event handlers
        """
        handlers: Set[EventHandler] = set()
        if event_type is None:
            # Get all handlers
            for handler_set in self._handlers.values():
                handlers.update(handler_set)
        else:
            # Get handlers for specific event type
            handlers.update(self._handlers.get(event_type, set()))
        return handlers

    def clear(self, event_type: Optional[EventType] = None) -> None:
        """Clear event handlers.

        Args:
            event_type: Type of event to clear handlers for, or None for all
        """
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            del self._handlers[event_type]


# Create default registry
default_registry = EventHandlerRegistry()

# Create default handlers
default_logger = LoggingHandler()
default_tracker = ChangeTracker()
default_validator = ValidationHandler()
default_cleanup = CleanupHandler()

# Register default handlers
default_registry.register(EventType.CHANGE, default_logger.handle_field_event)
default_registry.register(EventType.ERROR, default_logger.handle_field_event)
default_registry.register(EventType.VALIDATE, default_logger.handle_field_event)
default_registry.register(EventType.CHANGE, default_tracker.handle_field_event)
default_registry.register(EventType.VALIDATE, default_validator.handle_field_event)
default_registry.register(EventType.CLEANUP, default_cleanup.handle_field_event)
