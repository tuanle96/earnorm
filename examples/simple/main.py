"""Simple example usage."""

import asyncio
import json
import logging
from datetime import datetime

import earnorm
from earnorm import fields, models

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class User(models.BaseModel):
    """User model."""

    # Collection configuration
    _collection = "users"
    _name = "user"  # Model name
    _indexes = [{"email": 1}]  # MongoDB index format

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


async def print_connection_info():
    """Print detailed connection information."""
    connections = earnorm.pool.get_connection_info()
    logger.info("Connection Details:")
    logger.info("------------------")
    for conn in connections:
        logger.info(f"Connection ID: {conn.id}")
        logger.info(f"Created at: {datetime.fromtimestamp(conn.created_at)}")
        logger.info(f"Last used: {datetime.fromtimestamp(conn.last_used_at)}")
        logger.info(f"Idle time: {conn.idle_time:.2f}s")
        logger.info(f"Lifetime: {conn.lifetime:.2f}s")
        logger.info(f"Is stale: {conn.is_stale}")
        logger.info(f"Is available: {conn.is_available}")
        logger.info("------------------")


async def print_pool_health():
    """Print pool health information."""
    health = await earnorm.pool.get_health_check()
    logger.info("Pool Health Check:")
    logger.info("-----------------")
    logger.info(f"Status: {health['status']}")
    logger.info("\nStatistics:")
    logger.info(f"Average idle time: {health['statistics']['average_idle_time']:.2f}s")
    logger.info(f"Average lifetime: {health['statistics']['average_lifetime']:.2f}s")
    logger.info(f"Stale connections: {health['statistics']['stale_connections']}")
    logger.info(
        f"Connection usage: {health['statistics']['connection_usage']*100:.1f}%"
    )


async def cleanup_pool():
    """Cleanup stale connections."""
    cleaned = await earnorm.pool.cleanup_stale()
    logger.info(f"Cleaned up {cleaned} stale connections")


async def main():
    """Main function."""
    try:
        # Initialize EarnORM with pool configuration
        logger.info("Initializing EarnORM")
        mongo_uri = "mongodb://localhost:27017"
        await earnorm.init(
            mongo_uri=mongo_uri,
            database="earnorm_example",
            # Pool configuration
            min_pool_size=5,  # Minimum connections in pool
            max_pool_size=20,  # Maximum connections in pool
            pool_timeout=30.0,  # Timeout for acquiring connection
            pool_max_lifetime=3600,  # Max lifetime of connection in seconds
            pool_idle_timeout=300,  # Max idle time before cleanup
        )
        logger.info("EarnORM initialized successfully")

        # Print initial pool state
        await print_pool_metrics()
        await print_connection_info()
        await print_pool_health()

        # Get connection from pool for batch operations
        conn = await earnorm.get_connection()
        try:
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

            # Print pool state after creating users
            await print_pool_metrics()
            await print_pool_health()

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

            # Print pool state before cleanup
            await print_pool_metrics()
            await print_pool_health()

            # Cleanup stale connections
            await cleanup_pool()

            # Delete users
            logger.info("Deleting users")
            await all_users.unlink()
            logger.info("All users deleted")

            # Print final pool state
            await print_pool_metrics()
            await print_connection_info()
            await print_pool_health()

        finally:
            # Release connection back to pool
            await earnorm.release_connection(conn)

    except Exception as e:
        logger.error("Failed to run example: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
