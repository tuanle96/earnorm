"""Default security models."""

from datetime import datetime
from typing import Dict, List, Optional

from bson import ObjectId

from ..base.model import BaseModel
from .groups import group_manager
from .rbac import requires_permission


class Group(BaseModel):
    """Security group model."""

    _collection = "groups"
    _acl = {
        "create": ["admin"],
        "read": ["admin", "user"],
        "write": ["admin"],
        "delete": ["admin"],
    }

    name: str
    display_name: str
    category: str = "Other"
    parent_id: Optional[ObjectId] = None
    implied_groups: List[str] = []
    permissions: Dict[str, List[str]] = {}
    active: bool = True
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    async def save(self, *args, **kwargs):
        """Update timestamps and register group."""
        self.updated_at = datetime.utcnow()
        await super().save(*args, **kwargs)

        # Register group
        group_manager.register_group(
            name=self.name,
            category=self.category,
            parent=self.parent_id,
            implied_groups=self.implied_groups,
            permissions=self.permissions,
        )


class User(BaseModel):
    """User model."""

    _collection = "users"
    _acl = {
        "create": ["admin"],
        "read": ["admin", "user"],
        "write": ["admin"],
        "delete": ["admin"],
    }

    username: str
    password: str
    display_name: str
    email: str
    groups: List[str] = []
    is_superuser: bool = False
    is_admin: bool = False
    active: bool = True
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    async def save(self, *args, **kwargs):
        """Update timestamps."""
        self.updated_at = datetime.utcnow()
        await super().save(*args, **kwargs)

    @requires_permission("users", "write")
    async def set_password(self, password: str):
        """Set user password."""
        # TODO: Add password hashing
        self.password = password
        await self.save()

    def has_group(self, group: str) -> bool:
        """Check if user has group."""
        if self.is_superuser:
            return True
        return group_manager.check_membership(self.groups, group)

    def get_permissions(self) -> Dict[str, List[str]]:
        """Get user permissions."""
        if self.is_superuser:
            return {"*": ["*"]}  # All permissions
        return group_manager.get_permissions(self.groups)


async def create_default_groups():
    """Create default groups."""
    # User group
    await Group(
        name="group_user",
        display_name="Users",
        category="Base",
        permissions={"users": ["read"], "groups": ["read"]},
    ).save()

    # Admin group
    await Group(
        name="group_admin",
        display_name="Administrators",
        category="Base",
        implied_groups=["group_user"],
        permissions={
            "users": ["create", "read", "write", "delete"],
            "groups": ["create", "read", "write", "delete"],
        },
    ).save()


async def create_default_users():
    """Create default users."""
    # Superadmin user
    await User(
        username="superadmin",
        password="admin123",  # TODO: Hash password
        display_name="Super Administrator",
        email="superadmin@earnorm.local",
        is_superuser=True,
        is_admin=True,
    ).save()

    # Admin user
    await User(
        username="admin",
        password="admin123",  # TODO: Hash password
        display_name="Administrator",
        email="admin@earnorm.local",
        groups=["group_admin"],
        is_admin=True,
    ).save()


async def initialize_security():
    """Initialize security models and data."""
    await create_default_groups()
    await create_default_users()
