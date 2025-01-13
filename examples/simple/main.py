"""Simple example usage."""

import asyncio
import logging
import os

from models import User

from earnorm import init, registry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main function."""
    try:
        # Add models path to registry
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_file = os.path.join(current_dir, "models.py")
        registry.add_scan_path(models_file)

        # Initialize EarnORM
        logger.info("Initializing EarnORM")
        mongo_uri = "mongodb://localhost:27017"
        await init(
            mongo_uri=mongo_uri,
            database="earnorm_example",
        )
        logger.info("EarnORM initialized successfully")

        # Create a user
        logger.info("Creating user")
        user = User(name="John Doe", email="john@example.com", age=30)
        await user.save()
        logger.info("User created successfully")
    except Exception as e:
        logger.error("Failed to run example: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
