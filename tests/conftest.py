"""Test configuration and fixtures for EarnORM tests.

This module provides common fixtures and configuration for all tests.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from earnorm import init
from earnorm.base.env import Environment
from earnorm.base.database.adapters.mongo import MongoAdapter
from earnorm.config.data import SystemConfigData
from earnorm.di.container.base import Container
from earnorm.pool.backends.mongo import MongoPool
from earnorm.types.models import ModelProtocol


# Test configuration
TEST_CONFIG = {
    "database": {
        "mongodb": {
            "host": "localhost",
            "port": 27017,
            "database": "earnorm_test",
            "username": None,
            "password": None,
        }
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "database": 0,
        "password": None,
    },
    "pool": {
        "mongodb": {
            "min_size": 1,
            "max_size": 5,
            "max_idle_time": 300,
            "health_check_interval": 60,
        }
    },
}


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config_file() -> Generator[Path, None, None]:
    """Create a temporary configuration file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        import yaml
        yaml.dump(TEST_CONFIG, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest_asyncio.fixture
async def mock_mongo_client() -> AsyncGenerator[AsyncMongoMockClient, None]:
    """Create a mock MongoDB client for testing."""
    client = AsyncMongoMockClient()
    yield client
    client.close()


@pytest_asyncio.fixture
async def mock_mongo_database(mock_mongo_client: AsyncMongoMockClient) -> AsyncIOMotorDatabase[Dict[str, Any]]:
    """Create a mock MongoDB database for testing."""
    return mock_mongo_client.earnorm_test


@pytest_asyncio.fixture
async def test_config() -> SystemConfigData:
    """Create test configuration."""
    return SystemConfigData.from_dict(TEST_CONFIG)


@pytest_asyncio.fixture
async def test_container() -> AsyncGenerator[Container, None]:
    """Create a test dependency injection container."""
    container = Container()
    yield container
    await container.cleanup()


@pytest_asyncio.fixture
async def test_environment(
    test_config: SystemConfigData,
    test_container: Container,
    mock_mongo_database: AsyncIOMotorDatabase[Dict[str, Any]]
) -> AsyncGenerator[Environment, None]:
    """Create a test environment with mocked dependencies."""
    # Create mock MongoDB adapter
    adapter = MongoAdapter[ModelProtocol]()
    adapter._sync_db = mock_mongo_database
    
    # Register adapter in container
    test_container.register("mongodb_adapter", adapter)
    
    # Create environment
    env = Environment(config=test_config, container=test_container)
    
    yield env
    
    # Cleanup
    await env.cleanup()


@pytest_asyncio.fixture
async def mongo_adapter(
    mock_mongo_database: AsyncIOMotorDatabase[Dict[str, Any]]
) -> AsyncGenerator[MongoAdapter[ModelProtocol], None]:
    """Create a MongoDB adapter for testing."""
    adapter = MongoAdapter[ModelProtocol]()
    adapter._sync_db = mock_mongo_database
    
    yield adapter
    
    # Cleanup
    await adapter.cleanup()


@pytest.fixture
def sample_data() -> Dict[str, Any]:
    """Sample data for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "age": 25,
        "active": True,
        "tags": ["python", "testing"],
        "metadata": {
            "created_by": "test",
            "version": 1
        }
    }


@pytest.fixture
def sample_data_list() -> list[Dict[str, Any]]:
    """Sample data list for testing."""
    return [
        {
            "name": "User 1",
            "email": "user1@example.com",
            "age": 25,
            "active": True,
        },
        {
            "name": "User 2", 
            "email": "user2@example.com",
            "age": 30,
            "active": False,
        },
        {
            "name": "User 3",
            "email": "user3@example.com", 
            "age": 35,
            "active": True,
        }
    ]


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.slow = pytest.mark.slow


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Environment setup for tests
def setup_test_environment() -> None:
    """Setup test environment variables."""
    os.environ["EARNORM_ENV"] = "test"
    os.environ["EARNORM_LOG_LEVEL"] = "DEBUG"
    os.environ["EARNORM_DATABASE_MONGODB_DATABASE"] = "earnorm_test"


# Call setup on import
setup_test_environment()
