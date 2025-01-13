"""Simple example usage."""

import asyncio
import logging

import earnorm
from earnorm import BaseModel, Email, Int, String

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model."""

    # Collection configuration
    _collection = "users"
    _name = "user"  # Model name
    _indexes = [{"email": 1}]  # MongoDB index format

    # Fields
    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)


async def main():
    """Main function."""
    try:
        # Initialize EarnORM
        logger.info("Initializing EarnORM")
        mongo_uri = "mongodb://localhost:27017"
        await earnorm.init(
            mongo_uri=mongo_uri,
            database="earnorm_example",
        )
        logger.info("EarnORM initialized successfully")

        # Create multiple users
        logger.info("Creating users")
        users = [
            User(name="John Doe", email="john@example.com", age=30),
            User(name="Jane Smith", email="jane@example.com", age=25),
            User(name="Bob Wilson", email="bob@example.com", age=35),
        ]
        for user in users:
            await user.save()
        logger.info("Users created successfully")

        # Search users using domain
        logger.info("Searching users")
        users = await User.search([("age", ">", 25)])
        logger.info("Found %d users with age > 25", users.count())

        logger.info(users[0])

        # Sort users by age
        sorted_users = users.sorted("age", reverse=True)
        logger.info("Users sorted by age (desc):")
        for user in sorted_users:
            logger.info("- %s (age: %d)", user.name, user.age)

        # Filter users using domain
        adult_users = users.filtered_domain([("age", ">=", 30)])
        logger.info("Adult users (age >= 30):")
        for user in adult_users:
            logger.info("- %s (age: %d)", user.name, user.age)

        # Find single user
        logger.info("Finding user")
        user = await User.find_one([("email", "=", "john@example.com")])
        if user.exists():
            record = user.ensure_one()
            logger.info("User found:")
            logger.info("- Name: %s", record.name)
            logger.info("- Email: %s", record.email)
            logger.info("- Age: %d", record.age)
        else:
            logger.error("User not found")

        # Update user
        logger.info("Updating user")
        await user.write({"age": 31})
        logger.info("User age updated to: %d", user.ensure_one().age)

        # Map user names
        all_users = await User.search([])
        names = all_users.mapped("name")
        logger.info("All user names: %s", names)

        # Get first and last user (by insertion order)
        first_user = all_users.first()
        last_user = all_users.last()
        if first_user and last_user:
            logger.info("First user: %s", first_user.name)
            logger.info("Last user: %s", last_user.name)

        # Delete users
        logger.info("Deleting users")
        await all_users.unlink()
        logger.info("All users deleted")

    except Exception as e:
        logger.error("Failed to run example: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
