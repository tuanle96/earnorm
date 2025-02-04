"""Simple example usage with detailed logging.

This example demonstrates:
1. Model definition with auto env injection
2. CRUD operations with recordsets
3. Search and filtering
4. Error handling and logging
"""

import asyncio
import logging
from typing import Self

import earnorm
from earnorm import fields
from earnorm.base.model import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model with auto env injection.

    This model demonstrates:
    - Auto environment injection
    - Field definitions with validation
    - CRUD operations on recordsets

    Examples:
        >>> user = User()  # env auto-injected
        >>> new_user = await user.create({
        ...     "name": "John Doe",
        ...     "email": "john@example.com",
        ...     "age": 30
        ... })
        >>> print(new_user.name)  # Access as recordset
    """

    # Collection configuration
    _name = "user"

    # Fields with validation
    name = fields.StringField(required=True)
    email = fields.StringField(required=True, unique=True)
    age = fields.IntegerField(required=True)

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
        # Filter active users
        return users.filtered(lambda user: user.age is not None and user.age > 18)


async def main():
    """Main function demonstrating CRUD operations with User model.

    This function shows:
    1. Model instantiation with auto env injection
    2. Creating records
    3. Searching and filtering
    4. Updating records
    5. Deleting records
    6. Error handling

    Examples:
        >>> await main()
        Creating new user: John Doe
        Reading user by email: john@example.com
        Updating user age to 26
        Deleting user with email: john@example.com
    """
    try:
        # Initialize EarnORM
        await earnorm.init(
            config_path="examples/simple/config.yaml",
            cleanup_handlers=True,
            debug=True,
        )

        # CREATE - Create a new user
        new_user = await User.create(
            {"name": "John Doe", "email": "john@example.com", "age": 25}
        )
        logger.info(f"Created user: {new_user.name} with ID: {new_user.id}")

        # READ - Read/Search users
        # Get all adult users
        adult_users = await User.search(
            domain=[("age", ">", 18)],
            limit=10,
        )
        logger.info(f"Found {len(adult_users)} adult users")

        # Search by criteria
        users = await User.search(domain=[("email", "=", "john@example.com")], limit=1)
        if users:
            found_user = users[0]
            logger.info(f"Found user by email: {found_user.name}")

            # UPDATE - Update user information
            await found_user.write({"age": 26})
            logger.info(f"Updated user {found_user.name}'s age to {found_user.age}")

            # DELETE - Delete user
            success = await found_user.unlink()
            if success:
                logger.info(f"Deleted user: {found_user.name}")

        # Bulk operations example
        # Bulk update users under 20
        young_users = await User.search(domain=[("age", "<", 20)], limit=10)
        if young_users:
            await young_users.write({"age": 20})
            logger.info(f"Bulk updated {len(young_users)} users' age to 20")

        # Bulk delete users under 18
        underage_users = await User.search(domain=[("age", "<", 18)], limit=10)
        if underage_users:
            success = await underage_users.unlink()
            if success:
                logger.info(f"Bulk deleted {len(underage_users)} users")

    except Exception as e:
        logger.error(f"Error during CRUD operations: {str(e)}")
        raise
    finally:
        # Cleanup and close connections
        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            if env:
                await env.destroy()
                logger.info("Environment cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup environment: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
