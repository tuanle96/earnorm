"""Event class implementation."""

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
            Event data as dictionary
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
            data: Event data dictionary

        Returns:
            Event instance
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
            Event string
        """
        return f"Event(name={self.name}, data={self.data})"

    def __repr__(self) -> str:
        """Get detailed string representation of event.

        Returns:
            Detailed event string
        """
        return (
            f"Event(name={self.name}, data={self.data}, "
            f"metadata={self.metadata}, error={self.error}, "
            f"created_at={self.created_at}, failed_at={self.failed_at}, "
            f"job_id={self.job_id})"
        )
