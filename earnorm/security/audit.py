"""Audit logging management."""

from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Type, Union

from bson import ObjectId

from ..base.model import BaseModel


class AuditLog(BaseModel):
    """Model for audit logs."""

    _collection = "audit_logs"

    action: str
    collection: str
    document_id: ObjectId
    user_id: Optional[ObjectId]
    timestamp: datetime = datetime.utcnow()
    changes: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class AuditManager:
    """Manager for audit logging."""

    def __init__(self):
        self._tracked: Dict[str, Dict[str, Union[bool, List[str]]]] = {}

    def register_model(self, model: Type[BaseModel]) -> None:
        """Register audit configuration for a model."""
        if hasattr(model, "_audit"):
            collection = model._collection
            self._tracked[collection] = model._audit

    async def log(
        self,
        action: str,
        collection: str,
        document_id: ObjectId,
        user_id: Optional[ObjectId] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create an audit log entry."""
        await AuditLog(
            action=action,
            collection=collection,
            document_id=document_id,
            user_id=user_id,
            changes=changes or {},
            metadata=metadata or {},
        ).save()

    def should_track(
        self, collection: str, action: str, field: Optional[str] = None
    ) -> bool:
        """Check if action/field should be tracked."""
        if collection not in self._tracked:
            return False

        config = self._tracked[collection]
        if isinstance(config.get(action), bool):
            return config[action]
        elif isinstance(config.get(action), list):
            return field in config[action]
        return False

    async def get_logs(
        self,
        collection: str,
        document_id: ObjectId,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """Get audit logs for a document."""
        filters = {"collection": collection, "document_id": document_id}

        if action:
            filters["action"] = action
        if start_date:
            filters["timestamp"] = {"$gte": start_date}
        if end_date:
            filters.setdefault("timestamp", {})["$lte"] = end_date

        return await AuditLog.find(**filters).sort("timestamp", -1)


# Global audit manager instance
audit_manager = AuditManager()


def log(action: str, **metadata):
    """Decorator to log method execution."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = getattr(self.env, "user", None)
            user_id = user.id if user else None

            # Get old state for changes
            if hasattr(self, "id"):
                old_state = self.dict()
            else:
                old_state = {}

            # Execute method
            result = await func(self, *args, **kwargs)

            # Calculate changes
            if hasattr(self, "id"):
                new_state = self.dict()
                changes = {
                    field: {"old": old_state.get(field), "new": new_state[field]}
                    for field in new_state
                    if (field in old_state and new_state[field] != old_state.get(field))
                }
            else:
                changes = {}

            # Create audit log
            await audit_manager.log(
                action=action,
                collection=self._collection,
                document_id=self.id,
                user_id=user_id,
                changes=changes,
                metadata=metadata,
            )

            return result

        return wrapper

    return decorator
