"""Test suite for EarnORM."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import pytest

import earnorm
from earnorm import fields, models
from earnorm.validators import ValidationError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class User(models.BaseModel):
    """Test user model."""

    _collection = "test_users"
    _name = "test.user"
    _indexes = [{"email": 1}]

    _cache_enabled = True
    _cache_ttl = 300
    _cache_prefix = "test.user:"

    name = fields.String(required=True)
    email = fields.Email(required=True, unique=True)
    age = fields.Int(required=True)
    status = fields.String(required=False, default="active")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for pytest."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def earnorm_setup():
    """Initialize EarnORM."""
    logger.info("Initializing EarnORM for testing")
    await earnorm.init(
        mongo_uri="mongodb://localhost:27017",
        database="earnorm_test",
        redis_uri="redis://localhost:6379/0",
        cache_config={
            "ttl": 3600,
            "prefix": "test:",
            "max_retries": 3,
            "retry_delay": 1.0,
            "health_check_interval": 30.0,
        },
        min_pool_size=5,
        max_pool_size=20,
    )
    logger.info("EarnORM initialized successfully")
    yield
    # Cleanup after all tests
    logger.info("Cleaning up test data")
    conn = await earnorm.get_connection()
    try:
        await conn.database.drop_collection("test_users")
    finally:
        await earnorm.release_connection(conn)


@pytest.fixture
async def test_user(earnorm_setup) -> Optional[User]:
    """Create a test user."""
    logger.info("Creating test user")
    user = User(name="Test User", email="test@example.com", age=30)
    await user.save()
    logger.info(f"Test user created with ID: {user.id}")
    yield user
    # Cleanup
    if user.id:
        logger.info(f"Cleaning up test user {user.id}")
        await user.delete()


class TestUserModel:
    """Test cases for User model."""

    async def test_create_user(self, earnorm_setup):
        """Test user creation."""
        logger.info("Testing user creation")
        user = User(name="John Doe", email="john@example.com", age=30)
        await user.save()
        assert user.id is not None
        logger.info(f"User created successfully with ID: {user.id}")

        # Verify in database
        found = await User.find_one([("_id", "=", user.id)])
        assert found.exists()
        record = found.ensure_one()
        assert record.name == "John Doe"
        assert record.email == "john@example.com"
        assert record.age == 30
        logger.info("User verification successful")

        # Cleanup
        await user.delete()

    async def test_update_user(self, test_user):
        """Test user update."""
        logger.info(f"Testing update for user {test_user.id}")

        # Update via write
        logger.info("Updating user age to 31")
        original_id = test_user.id
        try:
            await test_user.write({"age": 31})
            logger.info("Update successful")

            # Verify update in database
            updated = await User.find_one([("_id", "=", original_id)])
            assert updated.exists()
            record = updated.ensure_one()
            assert record.age == 31
            logger.info("Update verification successful")

        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            logger.error(
                f"Current user state: ID={test_user.id}, Data={test_user.data}"
            )
            raise

    async def test_cache_invalidation(self, test_user):
        """Test cache invalidation on updates."""
        logger.info(f"Testing cache invalidation for user {test_user.id}")

        # First find to cache
        logger.info("Finding user (will be cached)")
        user = await User.find_one([("_id", "=", test_user.id)])
        assert user.exists()

        # Update user
        logger.info("Updating user to invalidate cache")
        await test_user.write({"age": 32})

        # Verify cache was invalidated
        cache_key = f"test.user:{test_user.id}"
        cached_value = await earnorm.cache.get(cache_key)
        assert cached_value is None
        logger.info("Cache invalidation verified")

    async def test_concurrent_updates(self, test_user):
        """Test concurrent updates to same user."""
        logger.info(f"Testing concurrent updates for user {test_user.id}")

        async def update_age(age: int):
            user = await User.find_one([("_id", "=", test_user.id)])
            logger.info(f"Updating age to {age}")
            await user.write({"age": age})

        # Try concurrent updates
        try:
            await asyncio.gather(update_age(33), update_age(34))

            # Verify final state
            final = await User.find_one([("_id", "=", test_user.id)])
            assert final.exists()
            logger.info(f"Final age after concurrent updates: {final.ensure_one().age}")

        except Exception as e:
            logger.error(f"Concurrent update failed: {str(e)}")
            raise

    async def test_validation(self, earnorm_setup):
        """Test validation rules."""
        logger.info("Testing validation rules")

        # Test required fields
        with pytest.raises(ValidationError) as exc:
            user = User(name="Test")  # Missing required fields
            await user.save()
        logger.info(f"Validation error caught: {str(exc.value)}")

        # Test invalid email
        with pytest.raises(ValidationError) as exc:
            user = User(name="Test", email="invalid-email", age=30)
            await user.save()
        logger.info(f"Email validation error caught: {str(exc.value)}")

        # Test invalid age
        with pytest.raises(ValidationError) as exc:
            user = User(name="Test", email="test@example.com", age="invalid")
            await user.save()
        logger.info(f"Age validation error caught: {str(exc.value)}")

    async def test_not_found_handling(self, earnorm_setup):
        """Test handling of not found cases."""
        logger.info("Testing not found handling")

        # Try to find non-existent user
        invalid_id = "507f1f77bcf86cd799439011"
        not_found = await User.find_one([("_id", "=", invalid_id)])
        assert not not_found.exists()
        logger.info("Not found case handled correctly")

        # Try to update non-existent user
        user = User(id=invalid_id)
        with pytest.raises(ValueError) as exc:
            await user.write({"age": 35})
        logger.info(f"Update of non-existent user failed as expected: {str(exc.value)}")

    async def test_search_and_browse(self, earnorm_setup):
        """Test search and browse operations."""
        logger.info("Testing search and browse operations")

        # Create test users
        users = [
            User(name=f"User {i}", email=f"user{i}@example.com", age=20 + i)
            for i in range(5)
        ]
        for user in users:
            await user.save()
        logger.info("Created 5 test users")

        try:
            # Test search
            logger.info("Testing search")
            results = await User.search([("age", ">", 22)])
            assert results.count() == 2
            logger.info(f"Search found {results.count()} users")

            # Test browse by IDs
            logger.info("Testing browse")
            user_ids = [str(user.id) for user in users]
            browsed = await User.browse(user_ids)
            assert browsed.count() == 5
            logger.info(f"Browse found {browsed.count()} users")

        finally:
            # Cleanup
            logger.info("Cleaning up test users")
            for user in users:
                await user.delete()

    async def test_cache_performance(self, test_user):
        """Test cache performance."""
        logger.info("Testing cache performance")

        # First query - from database
        start = datetime.now()
        user = await User.find_one([("_id", "=", test_user.id)])
        db_time = (datetime.now() - start).total_seconds()
        logger.info(f"Database query took {db_time:.4f} seconds")

        # Second query - from cache
        start = datetime.now()
        cached_user = await User.find_one([("_id", "=", test_user.id)])
        cache_time = (datetime.now() - start).total_seconds()
        logger.info(f"Cache query took {cache_time:.4f} seconds")

        # Verify cache is faster
        assert cache_time < db_time
        logger.info(f"Cache is {db_time/cache_time:.1f}x faster than database")
