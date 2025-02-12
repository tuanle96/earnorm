"""Simple example usage with detailed logging.

This module demonstrates:
1. Model definition with auto env injection
2. CRUD operations with recordsets
3. Search and filtering
4. Error handling and logging

Examples:
    >>> async def run():
    ...     await earnorm.init("config.yaml")
    ...     user = await User.create({
    ...         "name": "John",
    ...         "email": "john@example.com"
    ...     })
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
from earnorm.fields.relations.many_to_one import ManyToOneField
from earnorm.fields.relations.one_to_many import OneToManyField

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


# Define User model first since it will be referenced by other models
class User(BaseModel):
    """User model for demonstrating all types of relationships."""

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
    role = fields.EnumField(UserRole, default=UserRole.USER)

    # Many-to-One relationship
    manager: ManyToOneField["User"] = fields.ManyToOneField(
        "user", help="User's manager"
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


class Post(BaseModel):
    """Post model for demonstrating many-to-one relationships."""

    _name = "post"

    title = fields.StringField(required=True)
    content = fields.StringField(required=True)

    # Back reference to User
    author = fields.ManyToOneField(User, required=True, help="Post author")


class Department(BaseModel):
    """Department model for demonstrating one-to-many relationships."""

    _name = "department"

    name = fields.StringField(required=True)
    code = fields.StringField(required=True)

    # One2Many field - will be populated by reverse relation
    employees: OneToManyField[Employee] = fields.OneToManyField(
        "employee", related_name="department", help="Employees in this department"
    )


class Employee(BaseModel):
    """Employee model for demonstrating many-to-one relationships."""

    _name = "employee"

    name = fields.StringField(required=True)
    email = fields.StringField(
        required=True,
        unique=True,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )

    # Many2One field that creates the one2many reverse relation
    department: ManyToOneField["Department"] = fields.ManyToOneField(
        "department",
        related_name="employees",
        required=True,
        help="Employee's department",
    )


async def test_relationship_operations():
    """Test relationship operations."""
    logger.info("=== Testing Relationship Operations ===")

    try:
        # Test User-Post relationship (many2one)
        logger.info("=== Testing Many2One Relationship (User-Post) ===")

        # Create a manager
        logger.info("Creating manager...")
        manager = await User.create(
            {
                "name": "Manager",
                "email": "manager@example.com",
                "age": 40,
                "birth_date": date(1980, 1, 1),
            }
        )

        # Create users with manager
        logger.info("Creating users with manager...")
        user1 = await User.create(
            {
                "name": "Employee 1",
                "email": "emp1@example.com",
                "age": 25,
                "birth_date": date(1995, 1, 1),
                "manager": manager,  # Pass User instance
            }
        )

        user2 = await User.create(
            {
                "name": "Employee 2",
                "email": "emp2@example.com",
                "age": 30,
                "birth_date": date(1990, 1, 1),
                "manager": manager.id,  # Can use ID instead of instance
            }
        )

        # Create posts for users
        logger.info("Creating posts...")
        post1 = await Post.create(
            {
                "title": "First Post",
                "content": "Content of first post",
                "author": user1,  # Pass User instance
            }
        )

        post2 = await Post.create(
            {
                "title": "Second Post",
                "content": "Content of second post",
                "author": user2.id,  # Can use ID instead of instance
            }
        )

        # Verify relationships
        logger.info("Verifying many2one relationships...")

        # Check manager relationship
        emp1_manager = await user1.manager
        if emp1_manager:
            manager_name = await emp1_manager.name
            logger.info("Employee 1's manager: %s", manager_name)

        emp2_manager = await user2.manager
        if emp2_manager:
            manager_name = await emp2_manager.name
            logger.info("Employee 2's manager: %s", manager_name)

        # Check post author relationship
        post1_author = await post1.author
        if post1_author:
            author_name = await post1_author.name
            logger.info("Post 1's author: %s", author_name)

        post2_author = await post2.author
        if post2_author:
            author_name = await post2_author.name
            logger.info("Post 2's author: %s", author_name)

        # Test Department-Employee relationship (one2many)
        logger.info("\n=== Testing One2Many Relationship (Department-Employee) ===")

        # Create departments
        logger.info("Creating departments...")
        dev_dept = await Department.create({"name": "Development", "code": "DEV"})

        hr_dept = await Department.create({"name": "Human Resources", "code": "HR"})

        # Create employees in departments
        logger.info("Creating employees in department id: %s", dev_dept.id)
        dev_emp1 = await Employee.create(
            {"name": "Dev 1", "email": "dev1@example.com", "department": dev_dept}
        )
        logger.info("Created employee: %s", dev_emp1.id)

        logger.info("Creating employee in department id: %s", dev_dept.id)
        dev_emp2 = await Employee.create(
            {"name": "Dev 2", "email": "dev2@example.com", "department": dev_dept}
        )
        logger.info("Created employee: %s", dev_emp2.id)

        logger.info("Creating employee in department id: %s", hr_dept.id)
        hr_emp1 = await Employee.create(
            {"name": "HR 1", "email": "hr1@example.com", "department": hr_dept}
        )
        logger.info("Created employee: %s", hr_emp1.id)

        # Verify one2many relationships
        logger.info("Verifying one2many relationships...")

        # Get all employees in dev department
        dev_employees = await dev_dept.employees
        logger.info(f"Development department employees: {dev_employees}")
        for emp in dev_employees:
            emp_name = await emp.name
            logger.info(f"Department {await dev_dept.name} employee: {emp_name}")

        # Get all employees in HR department
        hr_employees = await hr_dept.employees
        logger.info("HR department employees:")
        for emp in hr_employees:
            emp_name = await emp.name
            logger.info("- %s", emp_name)

        # Verify department of employees
        dev1_dept = await dev_emp1.department
        logger.info(f"Dev1's department: {dev1_dept}")
        if dev1_dept:
            dept_name = await dev1_dept.name
            logger.info("Dev1's department: %s", dept_name)

        hr1_dept = await hr_emp1.department
        logger.info(f"HR1's department: {hr1_dept}")
        if hr1_dept:
            dept_name = await hr1_dept.name
            logger.info("HR1's department: %s", dept_name)

    except Exception as e:
        logger.error("Error in relationship operations: %s", str(e))
        raise


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
                "role": User.UserRole.ADMIN,
            }
        )
        logger.info("Created user: %s with email %s", user, await user.email)

        # READ - Get by ID
        logger.info("Reading user by ID...")
        user_id = user.id
        user = await User.browse(user_id)
        logger.info("Retrieved user: %s", user)

        # UPDATE - Modify fields
        logger.info("Updating user...")
        await user.write(
            {
                "name": "John Smith",
                "age": 26,
            }
        )
        logger.info("Updated user: %s", user)

        # DELETE - Remove record
        logger.info("Deleting user...")
        await user.unlink()
        logger.info("Deleted user with ID: %s", user_id)

    except Exception as e:
        logger.error("Error in single operations: %s", str(e))
        raise


async def test_bulk_operations():
    """Test bulk record operations."""
    logger.info("=== Testing Bulk Operations ===")

    try:
        # Bulk CREATE
        logger.info("Creating multiple users...")
        users = await User.create(
            [
                {
                    "name": f"User {i}",
                    "email": f"user{i}@example.com",
                    "age": 20 + i,
                    "birth_date": date(1990, 1, 1),
                }
                for i in range(5)
            ]
        )
        logger.info("Created %d users", len(users))

        # Bulk UPDATE
        logger.info("Updating multiple users...")
        await users.write(
            {
                "status": "junior",
            }
        )

        # Bulk DELETE
        logger.info("Deleting multiple users...")
        await users.unlink()
        logger.info("Deleted %d users", len(users))

    except Exception as e:
        logger.error("Error in bulk operations: %s", str(e))
        raise


async def test_search_operations():
    """Test search and filtering operations."""
    logger.info("=== Testing Search Operations ===")

    try:
        # Create test data
        await User.create(
            [
                {
                    "name": "Alice Smith",
                    "email": "alice@example.com",
                    "age": 25,
                    "birth_date": date(1990, 1, 1),
                    "salary": Decimal("6000.00"),
                    "is_active": True,
                },
                {
                    "name": "Bob Johnson",
                    "email": "bob@example.com",
                    "age": 30,
                    "birth_date": date(1985, 1, 1),
                    "salary": Decimal("7000.00"),
                    "is_active": True,
                },
                {
                    "name": "Charlie Brown",
                    "email": "charlie@example.com",
                    "age": 35,
                    "birth_date": date(1980, 1, 1),
                    "salary": Decimal("8000.00"),
                    "is_active": False,
                },
            ]
        )

        # Basic search
        logger.info("Performing basic search...")
        users = await User.search(domain=[("age", ">", 28)])
        logger.info("Found %d users over 28", len(users))

        # Complex search with multiple conditions
        logger.info("Performing complex search...")
        users = await User.search(
            domain=[
                ("is_active", "=", True),
                ("salary", ">=", 6500),
            ]
        )
        logger.info("Found %d active users with salary >= 6500.00", len(users))

        # Search with sorting
        logger.info("Performing sorted search...")
        users = await User.search(
            domain=[("is_active", "=", True)],
            order="salary desc",
        )
        logger.info("Found %d users, sorted by salary", len(users))

        # Search with limit and offset
        logger.info("Performing paginated search...")
        users = await User.search(
            domain=[],
            limit=2,
            offset=1,
            order="age asc",
        )
        logger.info("Found %d users (paginated)", len(users))

    except Exception as e:
        logger.error("Error in search operations: %s", str(e))
        raise


async def main():
    """Run all tests."""
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
        # await test_single_operations()
        # await test_bulk_operations()
        # await test_search_operations()
        await test_relationship_operations()

    except Exception as e:
        logger.error("Error in main: %s", str(e))
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
