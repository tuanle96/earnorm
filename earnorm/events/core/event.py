"""Event class implementation."""

from datetime import datetime
from typing import Any, Dict, Optional


class Event:
    """Base event class."""

    def __init__(
        self,
        name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        failed_at: Optional[datetime] = None,
    ):
        """Initialize event.

        Args:
            name: Event name
            data: Event data
            metadata: Optional event metadata
            error: Optional error message
            created_at: Optional creation timestamp
            failed_at: Optional failure timestamp
        """
        self.name = name
        self.data = data
        self.metadata = metadata or {}
        self.error = error
        self.created_at = created_at or datetime.now()
        self.failed_at = failed_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary.

        Returns:
            Event as dictionary
        """
        return {
            "name": self.name,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary.

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
        )

    def __str__(self) -> str:
        """String representation of event.

        Returns:
            Event string
        """
        return f"Event(name={self.name}, data={self.data})"

    def __repr__(self) -> str:
        """Detailed string representation of event.

        Returns:
            Detailed event string
        """
        return (
            f"Event(name={self.name}, data={self.data}, "
            f"metadata={self.metadata}, error={self.error}, "
            f"created_at={self.created_at}, failed_at={self.failed_at})"
        )
