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
from earnorm import BaseModel, fields

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
    status = fields.StringField(required=False)

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
        return await users.filtered(lambda user: user.age is not None and user.age > 18)


async def main():
    """Main function demonstrating CRUD operations with User model.

    This function shows:
    1. Single record operations:
       - Create single user
       - Read/Search single user
       - Update single user
       - Delete single user

    2. Bulk operations:
       - Create multiple users
       - Read/Search multiple users
       - Update multiple users
       - Delete multiple users
    """
    try:
        # Initialize EarnORM
        logger.info("Initializing ORM...")
        await earnorm.init(
            config_path="examples/simple/config.yaml",
            cleanup_handlers=True,
            debug=True,
        )
        logger.info("ORM initialized successfully")

        # ===== SINGLE RECORD OPERATIONS =====
        logger.info("=== Starting Single Record Operations ===")

        # CREATE - Create a new user
        logger.info("Creating new user...")
        new_user_one = await User.create(
            {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 25,
                "status": "active",
            }
        )
        logger.info(f"Created user: {await new_user_one.to_dict()}")

        await new_user_one.write({"age": 26})

        # try to delete
        await new_user_one.unlink()

        # # print slots
        # print(f"Slots for user one: {new_user_one.__slots__}")
        # print(f"Slots new_user_one|ids: {new_user_one._ids}")
        # print(f"Slots new_user_one|env: {new_user_one._env}")
        # print(f"Slots new_user_one|name: {new_user_one._name}")
        # print(f"Slots new_user_one|prefetch_ids: {new_user_one._prefetch_ids}")

        # CREATE - Create a new user
        # test_data = [
        #     {"name": "Alice Smith", "email": "alice@example.com", "age": 22},
        #     {"name": "Bob Johnson", "email": "bob@example.com", "age": 19},
        #     {"name": "Charlie Brown", "email": "charlie@example.com", "age": 25},
        #     {"name": "David Wilson", "email": "david@example.com", "age": 17},
        #     {"name": "Eve Anderson", "email": "eve@example.com", "age": 28},
        # ]
        # new_users = await User.create(test_data)
        # print(f"new_users: {new_users}")

        # test write
        # await new_users.write({"name": "Justin"})

        # first_new_users = new_users[0]
        # print(f"Slots first_new_users|ids: {first_new_users._ids}")
        # print(f"Slots first_new_users|env: {first_new_users._env}")
        # print(f"Slots first_new_users|name: {first_new_users._name}")
        # print(f"Slots first_new_users|prefetch_ids: {first_new_users._prefetch_ids}")

        # search
        justin_users = await User.search(domain=[])
        logger.info(f"justin_users: {len(justin_users)} with ids {justin_users.ids}")

        for justin in justin_users:
            logger.info(f"justin: {await justin.name}")
            logger.info(f"justin: {await justin.name}")

            # change name
            await justin.write({"name": "Justin 1"})

            # print cache
            logger.info(f"justin cache: {await justin.name}")

            # delete
            await justin.unlink()

            # try to get name
            logger.info(f"justin cache: {await justin.name}")

        # browse for first user to test prefetch
        # first_new_user = await User.browse("67a464fd7b6393d0963383d7")
        # print(f"Slots first_new_user|ids: {first_new_user._ids}")
        # print(f"Slots first_new_user|env: {first_new_user._env}")
        # print(f"Slots first_new_user|name: {first_new_user._name}")
        # print(f"Slots first_new_user|age: {await first_new_user.age}")
        # name_of_user = await first_new_user.age
        # print(f"name_of_user: {name_of_user}")

        # search
        # search_users = await User.search(domain=[("age", ">", 18)], limit=10)
        # print(f"Slots search_users|ids: {search_users._ids}")
        # print(f"Slots search_users|env: {search_users._env}")
        # print(f"Slots search_users|name: {search_users._name}")
        # print(f"Slots search_users|prefetch_ids: {search_users._prefetch_ids}")

        # # READ - Get user by ID
        # logger.info(f"Reading user by ID: {new_user.id}")
        # found_user = await User.browse(new_user.id)
        # if found_user:
        #     user_data = await found_user.to_dict()
        #     logger.info(
        #         f"Found user by ID: {user_data} by id {found_user.id} and email {found_user.email}"
        # )

        # READ - Search user by email
        # logger.info("Searching user by email: john@example.com")
        # users = await User.search(domain=[("email", "=", "john@example.com")])
        # if users:
        #     user_data = await users[0].to_dict()
        #     logger.info(
        #         f"Found user by email: {user_data} by email {users[0].email} and name {users[0].name}"
        #     )

        # UPDATE - Update user age
        # logger.info(f"Updating user {user_data['name']}'s age...")
        # await users[0].write({"age": 26})
        # updated_data = await users[0].to_dict()
        # logger.info(f"Updated user data: {updated_data}")

        # DELETE - Delete single user
        # logger.info(f"Deleting user: {updated_data['name']}")
        # success = await users[0].unlink()
        # logger.info(f"User deletion {'successful' if success else 'failed'}")

        # ===== BULK OPERATIONS =====
        # logger.info("=== Starting Bulk Operations ===")

        # BULK CREATE - Create multiple users
        # logger.info("Creating multiple users...")
        # bulk_users = []
        # test_data = [
        #     {"name": "Alice Smith", "email": "alice@example.com", "age": 22},
        #     {"name": "Bob Johnson", "email": "bob@example.com", "age": 19},
        #     {"name": "Charlie Brown", "email": "charlie@example.com", "age": 25},
        #     {"name": "David Wilson", "email": "david@example.com", "age": 17},
        #     {"name": "Eve Anderson", "email": "eve@example.com", "age": 28},
        # ]

        # for data in test_data:
        #     user = await User.create(data)
        #     bulk_users.append(user)  # type: ignore
        #     logger.info(f"Created user: {await user.to_dict()}")

        # # BULK READ - Search all users
        # logger.info("Searching all users...")
        # all_users = await User.search(domain=[], limit=10)
        # users_data = [await u.to_dict() for u in all_users]
        # logger.info(f"Found {len(all_users)} users: {users_data}")

        # # BULK READ - Search by age range
        # logger.info("Searching users by age range (18-25)...")
        # age_range_users = await User.search(
        #     domain=[("age", ">=", 18), ("age", "<=", 25)], limit=10
        # )
        # age_range_data = [await u.to_dict() for u in age_range_users]
        # logger.info(
        #     f"Found {len(age_range_users)} users in age range: {age_range_data}"
        # )

        # # BULK UPDATE - Update all adult users
        # logger.info("Updating all adult users...")
        # adult_users = await User.search(domain=[("age", ">=", 18)], limit=10)
        # if adult_users:
        #     await adult_users.write({"status": "active"})
        #     updated_data = [await u.to_dict() for u in adult_users]
        #     logger.info(f"Updated {len(adult_users)} adult users: {updated_data}")

        # # BULK DELETE - Delete users under 18
        # logger.info("Deleting users under 18...")
        # minor_users = await User.search(domain=[("age", "<", 18)], limit=10)
        # minor_data = [await u.to_dict() for u in minor_users]
        # logger.info(f"Found {len(minor_users)} users under 18: {minor_data}")
        # if minor_users:
        #     success = await minor_users.unlink()
        #     logger.info(
        #         f"Deletion of minor users {'successful' if success else 'failed'}"
        #     )

        # # Cleanup remaining users
        # logger.info("Cleaning up all remaining users...")
        # remaining_users = await User.search(domain=[], limit=100)
        # if remaining_users:
        #     await remaining_users.unlink()
        #     logger.info(f"Deleted {len(remaining_users)} remaining users")

    except Exception as e:
        logger.error(f"Error occurred: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup and close connections
        # logger.info("Cleaning up environment...")
        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            if env:
                await env.destroy()
                # logger.info("Environment cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup environment: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
