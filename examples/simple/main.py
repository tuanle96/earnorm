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
    email = fields.Email(required=True, unique=True)
    age = fields.Int(required=True)


async def print_pool_metrics():
    """Print connection pool metrics."""
    metrics = earnorm.pool.get_metrics()
    logger.info("Connection Pool Metrics:")
    logger.info("------------------------")
    logger.info(f"Total connections: {metrics.total_connections}")
    logger.info(f"Active connections: {metrics.active_connections}")
    logger.info(f"Available connections: {metrics.available_connections}")
    logger.info(f"Acquiring connections: {metrics.acquiring_connections}")
    logger.info(f"Min size: {metrics.min_size}")
    logger.info(f"Max size: {metrics.max_size}")
    logger.info(f"Timeout: {metrics.timeout}s")
    logger.info(f"Max lifetime: {metrics.max_lifetime}s")
    logger.info(f"Idle timeout: {metrics.idle_timeout}s")


async def main():
    """Main function."""
    try:
        # Initialize EarnORM with pool configuration
        logger.info("Initializing EarnORM")
        mongo_uri = "mongodb://localhost:27017"
        redis_uri = "redis://localhost:6379/0"
        await earnorm.init(
            mongo_uri=mongo_uri,
            database="earnorm_example",
            redis_uri=redis_uri,
            min_pool_size=5,
            max_pool_size=20,
            pool_timeout=30.0,
            pool_max_lifetime=3600,
            pool_idle_timeout=300,
        )
        logger.info("EarnORM initialized successfully")

        # Print initial pool state
        await print_pool_metrics()

        # Get connection from pool for batch operations
        conn = await earnorm.get_connection()
        try:
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
                logger.info("- %s (%s, %d years old)", user.name, user.email, user.age)

            # Find single user
            logger.info("Finding user by email")
            user = await User.find_one([("email", "=", "john@example.com")])
            if user.exists():
                record = user.ensure_one()
                logger.info("User found:")
                logger.info("- Name: %s", record.name)
                logger.info("- Email: %s", record.email)
                logger.info("- Age: %d", record.age)

            # Update user
            logger.info("Updating user")
            if user.exists():
                record = user.ensure_one()
                await record.write({"age": 31})
                logger.info("User age updated to: %d", record.age)

            # Find updated user
            logger.info("Finding updated user")
            updated_user = await User.find_one([("email", "=", "john@example.com")])
            if updated_user.exists():
                record = updated_user.ensure_one()
                logger.info("Updated user found:")
                logger.info("- Name: %s", record.name)
                logger.info("- Email: %s", record.email)
                logger.info("- Age: %d", record.age)

            # Delete users
            logger.info("Deleting users")
            all_users = await User.search([])
            for user in all_users:
                await user.delete()
            logger.info("All users deleted")

            # Print final pool state
            await print_pool_metrics()

        finally:
            # Release connection back to pool
            await earnorm.release_connection(conn)

    except Exception as e:
        logger.error("Failed to run example: %s", str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
