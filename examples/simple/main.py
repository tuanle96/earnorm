"""Simple example usage with detailed logging."""

import asyncio
import logging

import earnorm
from earnorm import fields, models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class User(models.BaseModel):
    """User model."""

    # Collection configuration
    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    # Fields
    name = fields.String(required=True)
    email = fields.String(required=True, unique=True)
    age = fields.Integer(required=True)


async def main():
    """Main function."""
    try:
        # Initialize EarnORM with pool configuration
        logger.info("Initializing EarnORM")
        await earnorm.init(config_path="examples/simple/config.json")
        logger.info("EarnORM initialized successfully")

        # Create users
        logger.info("Creating users")
        users = [
            User(name="John Doe", email="john@example.com", age=30),
            User(name="Jane Smith", email="jane@example.com", age=25),
            User(name="Bob Wilson", email="bob@example.com", age=35),
        ]

        for user in users:
            logger.debug(f"Saving user: {user.name}")
            await user.save()
        logger.info("Users created successfully")

        # Search users using domain
        logger.info("Searching users")
        users = await User.search([("age", ">", 25)])
        logger.info("Found %d users with age > 25", users.count())
        for user in users:
            logger.info("- %s (%s, %d years old)", user.name, user.email, user)

        # Find single user
        logger.info("Finding user by email")
        user = await User.find_one([("email", "=", "john@example.com")])
        if await user.exists():
            await user.ensure_one()
            logger.info("User found:")
            logger.info("- Name: %s", user.name)
            logger.info("- Email: %s", user.email)
            logger.info("- Age: %d", user.age)

        # Update user
        logger.info("Updating user")
        if await user.exists():
            await user.ensure_one()
            await user.write({"age": 31})
            logger.info("User age updated to: %d", user.age)

        # Find updated user
        logger.info("Finding updated user")
        updated_user = await User.find_one([("email", "=", "john@example.com")])
        if await updated_user.exists():
            await updated_user.ensure_one()
            logger.info("Updated user found:")
            logger.info("- Name: %s", updated_user.name)
            logger.info("- Email: %s", updated_user.email)
            logger.info("- Age: %d", updated_user.age)

        # Delete users
        logger.info("Deleting users")
        all_users = await User.search([])
        for user in all_users:
            await user.delete()
        logger.info("All users deleted")

    except Exception as e:
        logger.error("Failed to run example: %s", str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
