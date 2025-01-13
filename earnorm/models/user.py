"""User model for EarnORM."""

from datetime import datetime
from typing import List, Optional, Set

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field

from earnorm.base.model import BaseModel as OrmModel


class User(OrmModel):
    """User model with authentication and authorization."""

    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True},
        {"keys": [("username", 1)], "unique": True},
    ]

    # Basic fields
    id: str = Field(default_factory=lambda: str(ObjectId()))
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password_hash: str
    is_active: bool = True
    is_superuser: bool = False

    # Security fields
    groups: List[str] = []  # Group IDs
    permissions: Set[str] = set()  # Direct permissions
    last_login: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None  # User ID
    updated_by: Optional[str] = None  # User ID

    class Settings:
        """Model settings."""

        # Enable audit logging
        audit_enabled = True
        audit_fields = ["password_hash", "is_active", "groups", "permissions"]

        # Enable caching
        cache_enabled = True
        cache_ttl = 300  # 5 minutes

        # Security settings
        acl_enabled = True
        rbac_enabled = True
        encryption_fields = ["password_hash"]

    async def set_password(self, password: str) -> None:
        """Set user password.

        Args:
            password: Plain text password
        """
        from ..security.encryption import hash_password

        self.password_hash = await hash_password(password)
        self.password_changed_at = datetime.now(datetime.UTC)

    async def verify_password(self, password: str) -> bool:
        """Verify user password.

        Args:
            password: Plain text password to verify

        Returns:
            bool: True if password matches
        """
        from ..security.encryption import verify_password

        return await verify_password(password, self.password_hash)

    async def has_permission(self, permission: str) -> bool:
        """Check if user has permission.

        Args:
            permission: Permission to check

        Returns:
            bool: True if user has permission
        """
        # Superuser has all permissions
        if self.is_superuser:
            return True

        # Check direct permissions
        if permission in self.permissions:
            return True

        # Check group permissions
        from ..services.group import GroupService

        group_service = GroupService()
        return await group_service.check_permission(self.groups, permission)

    async def has_group(self, group_id: str) -> bool:
        """Check if user belongs to group.

        Args:
            group_id: Group ID to check

        Returns:
            bool: True if user belongs to group
        """
        return group_id in self.groups

    class Config:
        """Pydantic config."""

        json_encoders = {ObjectId: str}
