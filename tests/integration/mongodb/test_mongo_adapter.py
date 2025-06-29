"""Integration tests for MongoDB adapter.

This module tests the MongoDB adapter functionality including:
- Connection management
- CRUD operations
- Query building and execution
- Transaction handling
- Error handling and recovery
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from earnorm.base.database.adapters.mongo import MongoAdapter
from earnorm.base.model.base import BaseModel
from earnorm.fields.primitive.string import StringField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.exceptions import DatabaseError, ValidationError
from earnorm.types.models import ModelProtocol


class TestModel(BaseModel):
    """Test model for integration tests."""
    
    _name = "test_model"
    _table = "test_collection"
    
    name = StringField(required=True)
    value = IntegerField(default=0)
    active = BooleanField(default=True)


@pytest.mark.integration
class TestMongoAdapterConnection:
    """Test MongoDB adapter connection management."""
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = MongoAdapter[ModelProtocol]()

        assert adapter is not None
        assert adapter._pool_name == "default"
        assert adapter._pool is None
        assert adapter._db is None
    
    @pytest.mark.asyncio
    async def test_adapter_with_custom_pool_name(self):
        """Test adapter initialization with custom pool name."""
        adapter = MongoAdapter[ModelProtocol](pool_name="custom_pool")
        
        assert adapter._pool_name == "custom_pool"
    
    @pytest.mark.asyncio
    async def test_get_connection_without_init(self):
        """Test getting connection before initialization raises error."""
        adapter = MongoAdapter[ModelProtocol]()
        
        with pytest.raises(DatabaseError) as exc_info:
            await adapter.get_connection()
        
        assert "not initialized" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_adapter_cleanup(self):
        """Test adapter cleanup."""
        adapter = MongoAdapter[ModelProtocol]()
        
        # Should not raise any exception
        await adapter.cleanup()


@pytest.mark.integration
class TestMongoAdapterCRUDOperations:
    """Test MongoDB adapter CRUD operations."""
    
    @pytest.fixture
    async def mock_adapter(self, mock_mongo_database):
        """Create a mocked MongoDB adapter."""
        adapter = MongoAdapter[ModelProtocol]()
        adapter._db = mock_mongo_database
        return adapter
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "name": "Test Item",
            "value": 42,
            "active": True
        }
    
    @pytest.fixture
    def sample_data_list(self):
        """Sample data list for testing."""
        return [
            {"name": "Item 1", "value": 10, "active": True},
            {"name": "Item 2", "value": 20, "active": False},
            {"name": "Item 3", "value": 30, "active": True}
        ]
    
    @pytest.mark.asyncio
    async def test_create_single_record(self, mock_adapter, sample_data):
        """Test creating a single record."""
        # Mock collection insert
        collection = mock_adapter._get_collection(TestModel)
        collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="507f1f77bcf86cd799439011"))
        
        result = await mock_adapter.create(TestModel, sample_data)
        
        assert result == "507f1f77bcf86cd799439011"
        collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_multiple_records(self, mock_adapter, sample_data_list):
        """Test creating multiple records."""
        # Mock collection insert
        collection = mock_adapter._get_collection(TestModel)
        mock_result = MagicMock()
        mock_result.inserted_ids = ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012", "507f1f77bcf86cd799439013"]
        collection.insert_many = AsyncMock(return_value=mock_result)
        
        result = await mock_adapter.create(TestModel, sample_data_list)
        
        assert len(result) == 3
        assert all(isinstance(id_str, str) for id_str in result)
        collection.insert_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_single_record_by_id(self, mock_adapter, sample_data):
        """Test reading a single record by ID."""
        # Mock collection find
        collection = mock_adapter._get_collection(TestModel)
        expected_doc = {"_id": "507f1f77bcf86cd799439011", **sample_data}
        collection.find_one = AsyncMock(return_value=expected_doc)
        
        result = await mock_adapter.read(TestModel, "507f1f77bcf86cd799439011", [])
        
        assert result == expected_doc
        collection.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_multiple_records_by_ids(self, mock_adapter, sample_data_list):
        """Test reading multiple records by IDs."""
        # Mock collection find
        collection = mock_adapter._get_collection(TestModel)
        ids = ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
        expected_docs = [
            {"_id": ids[0], **sample_data_list[0]},
            {"_id": ids[1], **sample_data_list[1]}
        ]
        
        # Mock cursor
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=expected_docs)
        collection.find = MagicMock(return_value=mock_cursor)
        
        result = await mock_adapter.read(TestModel, ids, [])
        
        assert len(result) == 2
        assert result == expected_docs
        collection.find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_record(self, mock_adapter):
        """Test reading a nonexistent record returns None."""
        # Mock collection find
        collection = mock_adapter._get_collection(TestModel)
        collection.find_one = AsyncMock(return_value=None)
        
        result = await mock_adapter.read(TestModel, "nonexistent_id", [])
        
        assert result is None
        collection.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_single_record(self, mock_adapter, sample_data):
        """Test updating a single record."""
        # Mock collection update
        collection = mock_adapter._get_collection(TestModel)
        collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        
        filter_dict = {"_id": "507f1f77bcf86cd799439011"}
        update_data = {"name": "Updated Item"}
        
        result = await mock_adapter.update(TestModel, filter_dict, update_data)
        
        assert result == 1
        collection.update_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_multiple_records(self, mock_adapter):
        """Test updating multiple records."""
        # Mock collection update
        collection = mock_adapter._get_collection(TestModel)
        collection.update_many = AsyncMock(return_value=MagicMock(modified_count=3))
        
        filter_dict = {"active": True}
        update_data = {"value": 100}
        
        result = await mock_adapter.update(TestModel, filter_dict, update_data)
        
        assert result == 3
        collection.update_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_single_record(self, mock_adapter):
        """Test deleting a single record."""
        # Mock collection delete
        collection = mock_adapter._get_collection(TestModel)
        collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        
        filter_dict = {"_id": "507f1f77bcf86cd799439011"}
        
        result = await mock_adapter.delete(TestModel, filter_dict)
        
        assert result == 1
        collection.delete_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_multiple_records(self, mock_adapter):
        """Test deleting multiple records."""
        # Mock collection delete
        collection = mock_adapter._get_collection(TestModel)
        collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=3))
        
        filter_dict = {"active": False}
        
        result = await mock_adapter.delete(TestModel, filter_dict)
        
        assert result == 3
        collection.delete_many.assert_called_once()


@pytest.mark.integration
class TestMongoAdapterQueryOperations:
    """Test MongoDB adapter query operations."""
    
    @pytest.fixture
    async def mock_adapter(self, mock_mongo_database):
        """Create a mocked MongoDB adapter."""
        adapter = MongoAdapter[ModelProtocol]()
        adapter._sync_db = mock_mongo_database
        return adapter
    
    @pytest.mark.asyncio
    async def test_create_base_query(self, mock_adapter):
        """Test creating a base query."""
        query = await mock_adapter.query(TestModel, "base")
        
        assert query is not None
        # Additional query-specific assertions would go here
    
    @pytest.mark.asyncio
    async def test_create_aggregate_query(self, mock_adapter):
        """Test creating an aggregate query."""
        query = await mock_adapter.get_aggregate_query(TestModel)
        
        assert query is not None
        # Additional aggregate query-specific assertions would go here
    
    @pytest.mark.asyncio
    async def test_create_join_query(self, mock_adapter):
        """Test creating a join query."""
        join_query = await mock_adapter.get_join_query(TestModel)
        
        assert join_query is not None
        # Additional join query-specific assertions would go here


@pytest.mark.integration
class TestMongoAdapterErrorHandling:
    """Test MongoDB adapter error handling."""
    
    @pytest.fixture
    async def mock_adapter(self, mock_mongo_database):
        """Create a mocked MongoDB adapter."""
        adapter = MongoAdapter[ModelProtocol]()
        adapter._sync_db = mock_mongo_database
        return adapter
    
    @pytest.mark.asyncio
    async def test_create_with_database_error(self, mock_adapter, sample_data):
        """Test create operation with database error."""
        # Mock collection to raise exception
        collection = mock_adapter._get_collection(TestModel)
        collection.insert_one = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with pytest.raises(DatabaseError) as exc_info:
            await mock_adapter.create(TestModel, sample_data)
        
        assert "failed to create" in str(exc_info.value).lower()
        assert "mongodb" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_read_with_database_error(self, mock_adapter):
        """Test read operation with database error."""
        # Mock collection to raise exception
        collection = mock_adapter._get_collection(TestModel)
        collection.find_one = AsyncMock(side_effect=Exception("Database connection failed"))
        
        with pytest.raises(DatabaseError) as exc_info:
            await mock_adapter.read(TestModel, "507f1f77bcf86cd799439011", [])
        
        assert "failed to read" in str(exc_info.value).lower()
        assert "mongodb" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_update_with_database_error(self, mock_adapter):
        """Test update operation with database error."""
        # Mock collection to raise exception
        collection = mock_adapter._get_collection(TestModel)
        collection.update_one = AsyncMock(side_effect=Exception("Database connection failed"))
        
        filter_dict = {"_id": "507f1f77bcf86cd799439011"}
        update_data = {"name": "Updated Item"}
        
        with pytest.raises(DatabaseError) as exc_info:
            await mock_adapter.update(TestModel, filter_dict, update_data)
        
        assert "failed to update" in str(exc_info.value).lower()
        assert "mongodb" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_delete_with_database_error(self, mock_adapter):
        """Test delete operation with database error."""
        # Mock collection to raise exception
        collection = mock_adapter._get_collection(TestModel)
        collection.delete_one = AsyncMock(side_effect=Exception("Database connection failed"))
        
        filter_dict = {"_id": "507f1f77bcf86cd799439011"}
        
        with pytest.raises(DatabaseError) as exc_info:
            await mock_adapter.delete(TestModel, filter_dict)
        
        assert "failed to delete" in str(exc_info.value).lower()
        assert "mongodb" in str(exc_info.value).lower()


@pytest.mark.integration
class TestMongoAdapterUtilities:
    """Test MongoDB adapter utility methods."""
    
    @pytest.fixture
    async def mock_adapter(self, mock_mongo_database):
        """Create a mocked MongoDB adapter."""
        adapter = MongoAdapter[ModelProtocol]()
        adapter._sync_db = mock_mongo_database
        return adapter
    
    def test_get_collection_name_from_model(self, mock_adapter):
        """Test getting collection name from model class."""
        collection_name = mock_adapter._get_collection_name(TestModel)
        
        assert collection_name == "test_collection"
    
    def test_get_collection_name_from_string(self, mock_adapter):
        """Test getting collection name from string."""
        collection_name = mock_adapter._get_collection_name("custom_collection")
        
        assert collection_name == "custom_collection"
    
    def test_get_collection_object(self, mock_adapter):
        """Test getting collection object."""
        collection = mock_adapter._get_collection(TestModel)
        
        assert collection is not None
        assert hasattr(collection, 'find')
        assert hasattr(collection, 'insert_one')
        assert hasattr(collection, 'update_one')
        assert hasattr(collection, 'delete_one')
    
    def test_is_model_class_true(self, mock_adapter):
        """Test is_model_class returns True for model class."""
        result = mock_adapter.is_model_class(TestModel)
        
        assert result is True
    
    def test_is_model_class_false(self, mock_adapter):
        """Test is_model_class returns False for non-model class."""
        result = mock_adapter.is_model_class(str)
        
        assert result is False
    
    def test_is_model_instance_true(self, mock_adapter, mock_env):
        """Test is_model_instance returns True for model instance."""
        instance = TestModel(mock_env, name="test")
        result = mock_adapter.is_model_instance(instance)
        
        assert result is True
    
    def test_is_model_instance_false(self, mock_adapter):
        """Test is_model_instance returns False for non-model instance."""
        result = mock_adapter.is_model_instance("not a model")
        
        assert result is False
