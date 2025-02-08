"""Simple example usage with detailed logging.

This example demonstrates:
1. Model definition with auto env injection
2. CRUD operations with recordsets
3. Search and filtering
4. Error handling and logging
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Self

import earnorm
from earnorm import BaseModel, fields

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class Address(BaseModel):
    """Address model for demonstrating composite fields.

    Examples:
        >>> address = Address()
        >>> new_address = await address.create({
        ...     "street": "123 Main St",
        ...     "city": "New York",
        ...     "country": "USA",
        ...     "postal_code": "10001"
        ... })
    """

    _name = "address"

    street = fields.StringField(required=True)
    city = fields.StringField(required=True)
    country = fields.StringField(required=True)
    postal_code = fields.StringField(required=True)

    # Back reference to User
    user = fields.OneToOneField(
        "user",
        field="address_id",
        back_populates="address",
        required=True,
        ondelete="cascade",
        help="Related user",
    )


class Post(BaseModel):
    """Post model for demonstrating one-to-many relationships.

    Examples:
        >>> post = Post()
        >>> new_post = await post.create({
        ...     "title": "Hello World",
        ...     "content": "This is my first post",
        ...     "tags": ["hello", "world"]
        ... })
    """

    _name = "post"

    title = fields.StringField(required=True)
    content = fields.StringField(required=True)
    tags = fields.ListField(fields.StringField(), help="Post tags")

    # Back reference to User
    author = fields.ManyToOneField(
        "user",
        field="author_id",
        back_populates="posts",
        required=True,
        ondelete="cascade",
        help="Post author",
    )


class Group(BaseModel):
    """Group model for demonstrating many-to-many relationships.

    Examples:
        >>> group = Group()
        >>> new_group = await group.create({
        ...     "name": "Developers",
        ...     "description": "Group for developers"
        ... })
    """

    _name = "group"

    name = fields.StringField(required=True)
    description = fields.StringField(required=True)

    # Back reference to User
    members = fields.ManyToManyField(
        "user",
        back_populates="groups",
        help="Group members",
    )


class User(BaseModel):
    """User model for demonstrating all types of relationships.

    Examples:
        >>> user = User()
        >>> new_user = await user.create({
        ...     "name": "John Doe",
        ...     "email": "john@example.com",
        ...     "age": 30,
        ...     "salary": Decimal("5000.50"),
        ...     "is_active": True,
        ...     "birth_date": date(1990, 1, 1),
        ...     "last_login": datetime.now(),
        ...     "working_hours": time(9, 0, 0),
        ...     "preferences": {"theme": "dark", "notifications": True},
        ...     "tags": ["developer", "python"],
        ...     "role": UserRole.ADMIN
        ... })
    """

    _name = "user"

    # Enum for role field
    class UserRole(str, Enum):
        """User role enumeration."""

        ADMIN = "admin"
        USER = "user"
        GUEST = "guest"

    # Basic fields
    name = fields.StringField(required=True, min_length=2, max_length=100)
    email = fields.StringField(
        required=True,
        unique=True,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )
    age = fields.IntegerField(required=True, min_value=0, max_value=150)
    status = fields.StringField(required=False)

    # Number fields
    salary = fields.DecimalField(
        required=False, min_value=Decimal("0"), max_digits=10, decimal_places=2
    )
    score = fields.FloatField(
        required=False, min_value=0.0, max_value=100.0, default=0.0
    )

    # Boolean field
    is_active = fields.BooleanField(default=True)

    # Date/Time fields
    birth_date = fields.DateField(required=True)
    created_at = fields.DateTimeField(auto_now_add=True)
    updated_at = fields.DateTimeField(auto_now=True)
    last_login = fields.DateTimeField(required=False)
    working_hours = fields.TimeField(required=False)

    # Complex fields
    preferences = fields.JSONField(required=False, default=dict)
    tags = fields.ListField(fields.StringField(), required=False, default=list)
    role = fields.EnumField(UserRole, default=UserRole.USER)

    # One-to-One relationship
    address = fields.OneToOneField(
        "address",
        field="user_id",
        back_populates="user",
        required=True,
        ondelete="cascade",
        help="User's address",
    )

    # One-to-Many relationship
    posts = fields.OneToManyField(
        "post",
        back_populates="author",
        help="User's posts",
    )

    # Many-to-One relationship
    manager = fields.ManyToOneField(
        "user",
        field="manager_id",
        help="User's manager",
    )

    # Many-to-Many relationship
    groups = fields.ManyToManyField(
        "group",
        back_populates="members",
        help="User's groups",
    )

    async def get_adult_users(self) -> Self:
        """Retrieve and return all adult users from the database.

        Returns:
            Self: A recordset containing adult users

        Examples:
            >>> user = User()  # env auto-injected
            >>> adults = await user.get_adult_users()
            >>> for user in adults:
            ...     print(f"{user.name} ({user.age})")
        """
        # Search for users over 18
        users = await self.search(
            domain=[("age", ">", 18)],
            limit=10,
        )
        return users


async def test_single_operations():
    """Test single record CRUD operations."""
    logger.info("=== Testing Single Record Operations ===")

    try:
        # CREATE - Single record with all field types
        logger.info("Creating single user...")
        user = await User.create(
            {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 25,
                "status": "active",
                "salary": Decimal("5000.50"),
                "score": 95.5,
                "is_active": True,
                "birth_date": date(1990, 1, 1),
                "last_login": datetime.now(timezone.utc),
                "working_hours": time(9, 0, 0),
                "preferences": {"theme": "dark", "notifications": True},
                "tags": ["developer", "python"],
                "role": User.UserRole.ADMIN,
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "country": "USA",
                    "postal_code": "10001",
                },
                "manager_id": "manager_user_id",
                "group_ids": ["group1_id", "group2_id"],
            }
        )
        logger.info(f"Created user: {await user.to_dict()}")

        # READ - Single record
        logger.info(f"Reading user with ID: {user.id}")
        found_user = await User.browse(user.id)
        if found_user:
            logger.info(f"Found user: {await found_user.to_dict()}")

        # UPDATE - Single record with different field types
        logger.info("Updating user...")
        await user.write(
            {
                "age": 26,
                "status": "updated",
                "salary": Decimal("6000.00"),
                "score": 98.0,
                "is_active": False,
                "last_login": datetime.now(timezone.utc),
                "preferences": {"theme": "light"},
                "tags": ["senior", "developer", "python"],
                "role": User.UserRole.USER,
                "address": {
                    "street": "456 Elm St",
                    "city": "Los Angeles",
                    "country": "USA",
                    "postal_code": "90001",
                },
                "manager_id": "new_manager_user_id",
                "group_ids": ["group3_id"],
            }
        )
        logger.info(f"Updated user: {await user.to_dict()}")

        # DELETE - Single record
        logger.info("Deleting user...")
        success = await user.unlink()
        logger.info(f"User deletion: {'successful' if success else 'failed'}")

    except Exception as e:
        logger.error(f"Error in single operations test: {e}")
        raise


async def test_bulk_operations():
    """Test bulk CRUD operations."""
    logger.info("=== Testing Bulk Operations ===")

    try:
        # BULK CREATE
        logger.info("Creating multiple users...")
        test_data = [
            {"name": "Alice Smith", "email": "alice@example.com", "age": 22},
            {"name": "Bob Johnson", "email": "bob@example.com", "age": 19},
            {"name": "Charlie Brown", "email": "charlie@example.com", "age": 25},
            {"name": "David Wilson", "email": "david@example.com", "age": 17},
            {"name": "Eve Anderson", "email": "eve@example.com", "age": 28},
        ]
        users = await User.create(test_data)
        logger.info(f"Created {len(users)} users")

        # BULK READ
        logger.info("Reading all users...")
        all_users = await User.search(domain=[])
        for user in all_users:
            logger.info(f"User: {await user.to_dict()}")

        # BULK READ with filtering
        logger.info("Reading adult users...")
        adult_users = await User.search(domain=[("age", ">=", 18)])
        logger.info(f"Found {len(adult_users)} adult users")

        # BULK UPDATE
        logger.info("Updating all adult users...")
        await adult_users.write({"status": "adult"})
        logger.info("Updated status for adult users")

        # Verify updates
        updated_users = await User.search(domain=[("status", "=", "adult")])
        logger.info(f"Users with adult status: {len(updated_users)}")

        # BULK DELETE
        logger.info("Deleting all users...")
        all_users = await User.search(domain=[])
        success = await all_users.unlink()
        logger.info(f"Bulk deletion: {'successful' if success else 'failed'}")

    except Exception as e:
        logger.error(f"Error in bulk operations: {str(e)}", exc_info=True)
        raise


async def test_search_operations():
    """Test various search operations."""
    logger.info("=== Testing Search Operations ===")

    try:
        # Create test data
        test_data = [
            {
                "name": "Alice Smith",
                "email": "alice@example.com",
                "age": 22,
                "status": "active",
            },
            {
                "name": "Bob Johnson",
                "email": "bob@example.com",
                "age": 19,
                "status": "inactive",
            },
            {
                "name": "Charlie Brown",
                "email": "charlie@example.com",
                "age": 25,
                "status": "active",
            },
            {
                "name": "David Wilson",
                "email": "david@example.com",
                "age": 17,
                "status": "inactive",
            },
            {
                "name": "Eve Anderson",
                "email": "eve@example.com",
                "age": 28,
                "status": "active",
            },
        ]
        await User.create(test_data)

        # Search with multiple conditions
        logger.info("Searching active adult users...")
        active_adults = await User.search(
            domain=[("age", ">=", 18), ("status", "=", "active")]
        )
        logger.info(f"Found {len(active_adults)} active adult users")

        # Search with sorting
        logger.info("Searching users sorted by age...")
        sorted_users = await User.search(domain=[], order="age desc")
        for user in sorted_users:
            logger.info(f"User: {await user.to_dict()}")

        # Search with limit and offset
        logger.info("Searching with pagination...")
        paginated_users = await User.search(domain=[], limit=2, offset=1)
        logger.info(f"Found {len(paginated_users)} users in page")

        # Cleanup
        all_users = await User.search(domain=[])
        await all_users.unlink()

    except Exception as e:
        logger.error(f"Error in search operations: {str(e)}", exc_info=True)
        raise


async def test_relationship_operations():
    """Test relationship operations."""
    logger.info("=== Testing Relationship Operations ===")

    try:
        # 1. Test One-to-One relationship (User - Address)
        logger.info("Testing One-to-One relationship (User-Address)...")

        # Create user with address
        user = await User.create(
            {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 25,
                "birth_date": date(1990, 1, 1),
                "address": {
                    "street": "123 Main St",
                    "city": "New York",
                    "country": "USA",
                    "postal_code": "10001",
                },
            }
        )
        logger.info(f"Created user with address: {await user.to_dict()}")

        # Get user's address
        address = await user.address
        logger.info(f"User's address: {await address.to_dict()}")

        # 2. Test One-to-Many relationship (User - Posts)
        logger.info("Testing One-to-Many relationship (User-Posts)...")

        # Create posts for user
        post1 = await Post.create(
            {"title": "First Post", "content": "Hello World!", "author_id": user.id}
        )
        post2 = await Post.create(
            {"title": "Second Post", "content": "Another post", "author_id": user.id}
        )

        # Get user's posts
        user_posts = await user.posts
        logger.info(f"User has {len(user_posts)} posts")
        for post in user_posts:
            logger.info(f"Post: {await post.to_dict()}")

        # 3. Test Many-to-One relationship (User - Manager)
        logger.info("Testing Many-to-One relationship (User-Manager)...")

        # Create manager
        manager = await User.create(
            {
                "name": "Manager",
                "email": "manager@example.com",
                "age": 35,
                "birth_date": date(1985, 1, 1),
                "address": {
                    "street": "456 Boss St",
                    "city": "New York",
                    "country": "USA",
                    "postal_code": "10002",
                },
            }
        )

        # Set manager for user
        await user.write({"manager_id": manager.id})

        # Get user's manager
        user_manager = await user.manager
        logger.info(f"User's manager: {await user_manager.to_dict()}")

        # 4. Test Many-to-Many relationship (User - Groups)
        logger.info("Testing Many-to-Many relationship (User-Groups)...")

        # Create groups
        dev_group = await Group.create(
            {"name": "Developers", "description": "Development team"}
        )
        test_group = await Group.create(
            {"name": "Testers", "description": "Testing team"}
        )

        # Add user to groups
        await user.groups.add(dev_group)
        await user.groups.add(test_group)

        # Get user's groups
        user_groups = await user.groups
        logger.info(f"User belongs to {len(user_groups)} groups")
        for group in user_groups:
            logger.info(f"Group: {await group.to_dict()}")

        # Get group members
        dev_members = await dev_group.members
        logger.info(f"Developer group has {len(dev_members)} members")

        # Cleanup
        logger.info("Cleaning up relationship test data...")
        await user.unlink()  # This should cascade delete address and posts
        await manager.unlink()
        await dev_group.unlink()
        await test_group.unlink()

    except Exception as e:
        logger.error(f"Error in relationship operations test: {e}")
        raise


async def main():
    """Main function to run all tests."""
    try:
        # Initialize EarnORM
        logger.info("Initializing ORM...")
        await earnorm.init(
            config_path="examples/simple/config.yaml",
            cleanup_handlers=True,
            debug=True,
        )
        logger.info("ORM initialized successfully")

        # Run tests
        await test_single_operations()
        await test_bulk_operations()
        await test_search_operations()
        await test_relationship_operations()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup environment
        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            if env:
                await env.destroy()
                logger.info("Environment cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
