"""Event system for field changes.

This module provides the event system for tracking field changes:

Components:
- EventEmitter: Base class for objects that emit events
- EventBus: Central event dispatcher
- EventHandler: Type for event handler functions
- EventHandlerRegistry: Registry for event handlers

Events:
- EventType: Enum of event types (INIT, SETUP, VALIDATE, etc.)
- FieldEvent: Event data container

Handlers:
- LoggingHandler: Handler for logging field events (changes, errors, validation)
- ChangeTracker: Handler for tracking field changes in metadata
- ValidationHandler: Handler for field validation with retry support
- CleanupHandler: Handler for cleaning up field resources

Example:
    >>> class User(Model):
    ...     name = StringField()
    ...     age = IntegerField()
    ...
    ...     def on_name_change(self, event):
    ...         print(f"Name changed from {event.old_value} to {event.new_value}")
    ...
    >>> user = User()
    >>> user.name = "John"  # Triggers name_change event

Advanced Example:
    >>> # Create custom validation handler with retry
    >>> validator = ValidationHandler(max_retries=3, retry_delay=1.0)
    >>> bus = EventBus()
    >>> bus.subscribe(EventType.VALIDATE, validator.handle_field_event)
    >>>
    >>> # Create field with custom validation
    >>> class User(Model):
    ...     email = StringField(validators=[validate_email])
    ...
    >>> user = User()
    >>> await user.email.set("invalid")  # Will retry validation 3 times
"""

from earnorm.fields.events.base import EventEmitter, EventHandler, EventType, FieldEvent
from earnorm.fields.events.bus import EventBus
from earnorm.fields.events.handlers import (
    ChangeTracker,
    CleanupHandler,
    EventHandlerRegistry,
    FieldEventHandlerMixin,
    LoggingHandler,
    ValidationHandler,
    default_registry,
)

__all__ = [
    # Base classes
    "EventEmitter",
    "EventBus",
    "EventHandler",
    "EventHandlerRegistry",
    "FieldEventHandlerMixin",
    # Event types
    "EventType",
    "FieldEvent",
    # Handlers
    "LoggingHandler",
    "ChangeTracker",
    "ValidationHandler",
    "CleanupHandler",
    # Registry
    "default_registry",
]
