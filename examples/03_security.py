"""Example of using security features in EarnORM.

This example demonstrates:
1. Using ACL for model access control
2. Implementing record rules
3. Using RBAC for role-based permissions
4. Audit logging
5. Field-level encryption
"""

from datetime import datetime
from typing import Optional

from earnorm import BaseModel, fields
from earnorm.security import acl, audit, rbac


class User(BaseModel):
    """User model with security features."""

    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True},
        {"keys": [("username", 1)], "unique": True},
    ]

    # Define ACL rules
    _acl = {
        "create": ["system", "admin"],
        "read": ["*"],  # Public read access
        "write": ["admin", "user_manager"],
        "delete": ["admin"],
    }

    # Define record rules
    _rules = {
        "user_access": lambda self, user: (
            user.has_group("admin") or self.id == user.id
        ),
        "active_only": lambda self, user: self.active,
    }

    username = fields.Char(string="Username", required=True, unique=True)
    email = fields.Email(string="Email", required=True, unique=True)
    password = fields.Password(string="Password", required=True)
    name = fields.Char(string="Full Name", required=True)
    phone = fields.Phone(string="Phone")
    role_ids = fields.Many2many("roles", string="Roles")
    active = fields.Boolean(string="Active", default=True)

    # Encrypted fields
    ssn = fields.Encrypted(fields.Char(string="SSN"))
    bank_account = fields.Encrypted(fields.Char(string="Bank Account"))

    async def check_access(self, operation: str, user) -> bool:
        """Check if user has access to perform operation."""
        # Check ACL first
        if not await acl.check_access(self, operation, user):
            return False

        # Check record rules
        if operation in ("read", "write", "delete"):
            if not await self.check_rules(user):
                return False

        return True

    async def on_change(self, changes: dict) -> None:
        """Log changes to audit log."""
        await audit.log_changes(
            model=self._collection,
            record_id=self.id,
            changes=changes,
            user_id=self.env.user.id,
            timestamp=datetime.utcnow(),
        )


class Role(BaseModel):
    """Role model for RBAC."""

    _collection = "roles"
    _indexes = [{"keys": [("name", 1)], "unique": True}]

    name = fields.Char(string="Name", required=True, unique=True)
    description = fields.Text(string="Description")
    permissions = fields.Many2many("permissions", string="Permissions")
    user_ids = fields.Many2many("users", string="Users")


async def example_usage():
    """Example of using security features."""
    from earnorm import env

    # Create admin role
    admin_role = await env["roles"].create(
        {"name": "admin", "description": "Administrator role"}
    )

    # Create user manager role
    user_manager = await env["roles"].create(
        {"name": "user_manager", "description": "User management role"}
    )

    # Create admin user
    admin = await env["users"].create(
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",
            "name": "System Admin",
            "role_ids": [admin_role.id],
            "ssn": "123-45-6789",
            "bank_account": "1234567890",
        }
    )

    # Create regular user
    user = await env["users"].create(
        {
            "username": "john",
            "email": "john@example.com",
            "password": "john123",
            "name": "John Doe",
            "role_ids": [],
            "ssn": "987-65-4321",
            "bank_account": "0987654321",
        }
    )

    # Check access
    can_create = await env["users"].check_access("create", admin)
    can_read = await user.check_access("read", user)
    can_write = await user.check_access("write", user)
    can_delete = await user.check_access("delete", user)

    print(f"Admin can create users: {can_create}")
    print(f"User can read own record: {can_read}")
    print(f"User can write own record: {can_write}")
    print(f"User can delete own record: {can_delete}")

    # Update user (will trigger audit log)
    await user.write({"name": "John Smith", "phone": "+1234567890"})

    # Get audit logs
    logs = await audit.get_logs(
        model="users", record_id=user.id, start_date=datetime(2024, 1, 1)
    )

    print("\nAudit Logs:")
    for log in logs:
        print(f"Change by {log.user_id} at {log.timestamp}:")
        for field, (old_value, new_value) in log.changes.items():
            print(f"  {field}: {old_value} -> {new_value}")

    # Encrypted fields are automatically decrypted
    print(f"\nDecrypted SSN: {user.ssn}")
    print(f"Decrypted Bank Account: {user.bank_account}")

    # But raw database values are encrypted
    db_user = await env.db["users"].find_one({"_id": user.id})
    print(f"Encrypted SSN in DB: {db_user['ssn']}")
    print(f"Encrypted Bank Account in DB: {db_user['bank_account']}")
