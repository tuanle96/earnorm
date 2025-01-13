"""Simple example usage."""

import asyncio
import logging

from models import User

import earnorm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

        # Create a user
        logger.info("Creating user")
        user = User(name="John Doe", email="john@example.com", age=30)
        await user.save()
        logger.info("User created successfully")

        # Find a user
        logger.info("Finding user")
        user = await User.find_one([("email", "=", "john@example.com")])
        if user:
            logger.info("User found: %s", user)
            logger.info("User email: %s", user.email)
            logger.info("User age: %s", user.age)
            logger.info("User name: %s", user.name)
        else:
            logger.error("User not found")

    except Exception as e:
        logger.error("Failed to run example: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
