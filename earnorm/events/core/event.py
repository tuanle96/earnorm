"""Event class implementation.

This module provides the Event class for handling events in the system.
Events are used to represent actions or state changes that can be published and processed.

Features:
- Event creation and serialization
- Metadata and error handling
- Timestamp tracking
- BullMQ compatibility

Examples:
    ```python
    # Create event
    event = Event(
        name="user.created",
        data={"id": "123", "name": "John"},
        metadata={"source": "api"}
    )

    # Convert to dict for serialization
    event_dict = event.to_dict()

    # Create from dict
    event = Event.from_dict(event_dict)
    ```
"""

from datetime import datetime
from typing import Any, Dict, Optional


class Event:
    """Base event class for handling events in the system.

    This class represents an event that can be published and processed by the event system.
    It is designed to be compatible with BullMQ while maintaining the existing functionality.

    Attributes:
        name: Event name/type
        data: Event payload data
        metadata: Additional event metadata
        error: Error message if event processing failed
        created_at: Event creation timestamp
        failed_at: Event failure timestamp if failed
        job_id: BullMQ job ID for tracking

    Examples:
        ```python
        # Create simple event
        event = Event("user.created", {"id": "123"})

        # Create event with metadata
        event = Event(
            name="order.completed",
            data={"order_id": "456"},
            metadata={"source": "payment_service"}
        )

        # Create failed event
        event = Event(
            name="email.send",
            data={"to": "user@example.com"},
            error="Failed to connect to SMTP server"
        )
        ```
    """

    def __init__(
        self,
        name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        failed_at: Optional[datetime] = None,
        job_id: Optional[str] = None,
    ):
        """Initialize event.

        Args:
            name: Event name/type
            data: Event payload data
            metadata: Optional event metadata
            error: Optional error message
            created_at: Optional creation timestamp
            failed_at: Optional failure timestamp
            job_id: Optional BullMQ job ID

        Examples:
            ```python
            # Create event with all fields
            event = Event(
                name="user.created",
                data={"id": "123"},
                metadata={"source": "api"},
                error=None,
                created_at=datetime.now(),
                job_id="job_123"
            )
            ```
        """
        self.name = name
        self.data = data
        self.metadata = metadata or {}
        self.error = error
        self.created_at = created_at or datetime.now()
        self.failed_at = failed_at
        self.job_id = job_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format for serialization.

        Returns:
            Event data as dictionary with all fields serialized to JSON-compatible format.
            Timestamps are converted to ISO format strings.

        Examples:
            ```python
            event = Event("user.created", {"id": "123"})
            event_dict = event.to_dict()
            # {
            #     "name": "user.created",
            #     "data": {"id": "123"},
            #     "metadata": {},
            #     "error": null,
            #     "created_at": "2024-01-15T12:00:00",
            #     "failed_at": null,
            #     "job_id": null
            # }
            ```
        """
        return {
            "name": self.name,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "job_id": self.job_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event instance from dictionary data.

        Args:
            data: Event data dictionary containing serialized event fields.
                 Timestamps should be in ISO format strings.

        Returns:
            Event instance initialized with the deserialized data.

        Examples:
            ```python
            event_dict = {
                "name": "user.created",
                "data": {"id": "123"},
                "metadata": {"source": "api"},
                "created_at": "2024-01-15T12:00:00"
            }
            event = Event.from_dict(event_dict)
            ```
        """
        created_at = (
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        )
        failed_at = (
            datetime.fromisoformat(data["failed_at"]) if data.get("failed_at") else None
        )

        return cls(
            name=data["name"],
            data=data["data"],
            metadata=data.get("metadata"),
            error=data.get("error"),
            created_at=created_at,
            failed_at=failed_at,
            job_id=data.get("job_id"),
        )

    def __str__(self) -> str:
        """Get string representation of event.

        Returns:
            Event string in format "Event(name=<name>, data=<data>)".

        Examples:
            ```python
            event = Event("user.created", {"id": "123"})
            str(event)  # "Event(name=user.created, data={'id': '123'})"
            ```
        """
        return "Event(name=%s, data=%s)" % (self.name, self.data)

    def __repr__(self) -> str:
        """Get detailed string representation of event.

        Returns:
            Detailed event string including all fields.

        Examples:
            ```python
            event = Event("user.created", {"id": "123"})
            repr(event)  # "Event(name=user.created, data={'id': '123'}, metadata={}, ...)"
            ```
        """
        return (
            "Event(name=%s, data=%s, metadata=%s, error=%s, created_at=%s, "
            "failed_at=%s, job_id=%s)"
            % (
                self.name,
                self.data,
                self.metadata,
                self.error,
                self.created_at,
                self.failed_at,
                self.job_id,
            )
        )
