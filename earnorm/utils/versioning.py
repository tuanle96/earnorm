"""Versioning utilities for EarnORM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId


class Version:
    """Represents a version of a field value."""

    def __init__(
        self,
        old_value: Any,
        new_value: Any,
        timestamp: datetime,
        context: Dict[str, Any],
    ) -> None:
        """Initialize version."""
        self.id = ObjectId()
        self.old_value = old_value
        self.new_value = new_value
        self.timestamp = timestamp
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            "id": str(self.id),
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class VersionManager:
    """Manager for field versioning."""

    def __init__(self) -> None:
        """Initialize version manager."""
        self._versions: List[Version] = []

    async def track_change(
        self,
        old_value: Any,
        new_value: Any,
        max_versions: int = 10,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track a value change."""
        # Skip if values are equal
        if old_value == new_value:
            return

        # Create new version
        version = Version(
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now(timezone.utc),
            context=context or {},
        )

        # Add to versions list
        self._versions.append(version)

        # Trim old versions if needed
        if max_versions > 0 and len(self._versions) > max_versions:
            self._versions = self._versions[-max_versions:]

    async def get_versions(
        self, limit: Optional[int] = None, skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Get version history."""
        versions = self._versions[skip:]
        if limit is not None:
            versions = versions[:limit]
        return [v.to_dict() for v in versions]

    def clear_versions(self) -> None:
        """Clear all versions."""
        self._versions = []

    def get_latest_version(self) -> Optional[Version]:
        """Get latest version."""
        if not self._versions:
            return None
        return self._versions[-1]

    def get_version_count(self) -> int:
        """Get number of versions."""
        return len(self._versions)
