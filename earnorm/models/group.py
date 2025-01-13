"""Group model for EarnORM."""

from datetime import datetime
from typing import List, Optional, Set

from bson import ObjectId
from pydantic import Field

from ..base.model import BaseModel as OrmModel


class Group(OrmModel):
    """Group model for role-based access control."""

    _collection = "groups"
    _indexes = [{"keys": [("name", 1)], "unique": True}]

    # Basic fields
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str = Field(min_length=3, max_length=50)
    description: Optional[str] = None
    is_active: bool = True

    # Security fields
    permissions: Set[str] = set()  # Group permissions
    parent_groups: List[str] = []  # Parent group IDs for inheritance

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # User ID
    updated_by: Optional[str] = None  # User ID

    class Settings:
        """Model settings."""

        # Enable audit logging
        audit_enabled = True
        audit_fields = ["name", "is_active", "permissions", "parent_groups"]

        # Enable caching
        cache_enabled = True
        cache_ttl = 300  # 5 minutes

        # Security settings
        acl_enabled = True
        rbac_enabled = True

    async def has_permission(self, permission: str) -> bool:
        """Check if group has permission.

        Args:
            permission: Permission to check

        Returns:
            bool: True if group has permission
        """
        # Check direct permissions
        if permission in self.permissions:
            return True

        # Check parent group permissions
        if self.parent_groups:
            from ..services.group import GroupService

            group_service = GroupService()
            return await group_service.check_permission(self.parent_groups, permission)

        return False

    async def get_all_permissions(self) -> Set[str]:
        """Get all permissions including inherited ones.

        Returns:
            Set[str]: All permissions
        """
        # Start with direct permissions
        all_permissions = self.permissions.copy()

        # Add parent group permissions
        if self.parent_groups:
            from ..services.group import GroupService

            group_service = GroupService()
            parent_permissions = await group_service.get_permissions(self.parent_groups)
            all_permissions.update(parent_permissions)

        return all_permissions

    class Config:
        """Pydantic config."""

        json_encoders = {ObjectId: str}
