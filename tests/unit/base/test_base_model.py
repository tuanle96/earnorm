"""Unit tests for BaseModel class.

This module tests the core functionality of the BaseModel class including:
- Model creation and initialization
- Field validation and type checking
- CRUD operations
- Model metadata and registry
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from earnorm.base.model.base import BaseModel
from earnorm.base.env import Environment
from earnorm.fields.primitive.string import StringField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.exceptions import ValidationError, EarnORMError


class TestUser(BaseModel):
    """Test model for unit tests."""

    _name = "test_user"

    name = StringField(required=True, max_length=100)
    email = StringField(required=True)
    age = IntegerField()
    active = BooleanField()


class TestBaseModelCreation:
    """Test BaseModel creation and initialization."""

    def test_model_class_attributes(self):
        """Test that model class has correct attributes."""
        assert TestUser._name == "test_user"
        assert hasattr(TestUser, "name")
        assert hasattr(TestUser, "email")
        assert hasattr(TestUser, "age")
        assert hasattr(TestUser, "active")

    def test_model_fields_are_field_instances(self):
        """Test that model fields are proper field instances."""
        # Note: In EarnORM, fields are accessed through descriptors
        # We need to check the field definitions on the class
        assert hasattr(TestUser, "__fields__")
        fields = TestUser.__fields__
        assert "name" in fields
        assert "email" in fields
        assert "age" in fields
        assert "active" in fields

    def test_field_configuration(self):
        """Test that fields are configured correctly."""
        # Access field instances through the class __dict__
        name_field = TestUser.__dict__["name"]
        email_field = TestUser.__dict__["email"]
        age_field = TestUser.__dict__["age"]
        active_field = TestUser.__dict__["active"]

        assert isinstance(name_field, StringField)
        assert isinstance(email_field, StringField)
        assert isinstance(age_field, IntegerField)
        assert isinstance(active_field, BooleanField)

        assert name_field.required is True
        assert name_field.max_length == 100
        assert email_field.required is True


class TestBaseModelInstantiation:
    """Test BaseModel instance creation."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = MagicMock(spec=Environment)
        env.container = MagicMock()
        env.config = MagicMock()
        env._initialized = True
        return env

    def test_create_instance_basic(self, mock_env):
        """Test creating basic model instance."""
        # In EarnORM, BaseModel constructor only takes env parameter
        user = TestUser(env=mock_env)

        assert user._env == mock_env
        assert user._name == "test_user"
        assert user._ids == ()
        assert isinstance(user._cache, dict)

    def test_create_instance_without_env_fails(self):
        """Test creating instance without environment fails."""
        with patch.object(TestUser, '_get_default_env', return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                TestUser()

            assert "Environment not initialized" in str(exc_info.value)

    def test_create_instance_with_default_env(self):
        """Test creating instance with default environment."""
        mock_env = MagicMock(spec=Environment)
        mock_env._initialized = True

        with patch.object(TestUser, '_get_default_env', return_value=mock_env):
            user = TestUser()
            assert user._env == mock_env


class TestBaseModelValidation:
    """Test BaseModel field validation."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = MagicMock(spec=Environment)
        env.container = MagicMock()
        env.config = MagicMock()
        env._initialized = True
        return env

    @pytest.fixture
    def valid_user(self, mock_env):
        """Create a valid user instance."""
        return TestUser(env=mock_env)

    @pytest.mark.asyncio
    async def test_field_validation_string_length(self):
        """Test string field validation for length constraints."""
        name_field = TestUser.__dict__["name"]

        # Valid string
        result = await name_field.validate("John Doe")
        assert result == "John Doe"

        # String too long
        with pytest.raises(ValueError) as exc_info:
            await name_field.validate("x" * 101)
        assert "length" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_field_validation_required(self):
        """Test required field validation."""
        name_field = TestUser.__dict__["name"]
        email_field = TestUser.__dict__["email"]

        # Required field with None should fail
        with pytest.raises(ValidationError):
            await name_field.validate(None)

        with pytest.raises(ValidationError):
            await email_field.validate(None)


class TestBaseModelCRUDOperations:
    """Test BaseModel CRUD operations."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment with mocked adapter."""
        env = MagicMock(spec=Environment)
        env.container = MagicMock()
        env.config = MagicMock()
        env._initialized = True

        # Mock database adapter
        adapter = AsyncMock()
        env.adapter = adapter

        return env

    @pytest.fixture
    def valid_user_data(self):
        """Valid user data for testing."""
        return {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "active": True
        }

    @pytest.mark.asyncio
    async def test_create_single_record(self, mock_env, valid_user_data):
        """Test creating a single record."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439011"

        # Mock the _get_env method to return our mock environment
        with patch.object(TestUser, '_get_env', return_value=mock_env):
            with patch.object(TestUser, '_convert_to_db', return_value=valid_user_data):
                result = await TestUser.create(valid_user_data)

                # Verify adapter was called correctly
                adapter.create.assert_called_once()

                # Verify result is a recordset
                assert isinstance(result, TestUser)
    
    @pytest.mark.asyncio
    async def test_browse_by_id(self, mock_env):
        """Test browsing records by ID."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.read.return_value = {
            "_id": "507f1f77bcf86cd799439011",
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "active": True
        }

        # Mock the _get_env method to return our mock environment
        with patch.object(TestUser, '_get_env', return_value=mock_env):
            result = await TestUser.browse("507f1f77bcf86cd799439011")

            # Verify result is a TestUser recordset
            assert isinstance(result, TestUser)

    @pytest.mark.asyncio
    async def test_search_records(self, mock_env):
        """Test searching records."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock

        # Mock the _get_env method to return our mock environment
        with patch.object(TestUser, '_get_env', return_value=mock_env):
            result = await TestUser.search([("name", "=", "John")])

            # Verify result is a TestUser recordset
            assert isinstance(result, TestUser)

    @pytest.mark.asyncio
    async def test_unlink_record(self, mock_env):
        """Test deleting a record."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.delete.return_value = 1  # Number of deleted records

        user = TestUser(env=mock_env)
        user._ids = ("507f1f77bcf86cd799439011",)

        with patch.object(user, '_unlink', return_value=None):
            result = await user.unlink()

            # Verify result
            assert result is True


class TestBaseModelUtilities:
    """Test BaseModel utility methods."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = MagicMock(spec=Environment)
        env.container = MagicMock()
        env.config = MagicMock()
        env._initialized = True
        return env

    def test_model_name_property(self, mock_env):
        """Test model name property."""
        user = TestUser(env=mock_env)
        assert user._name == "test_user"

    def test_model_env_property(self, mock_env):
        """Test model environment property."""
        user = TestUser(env=mock_env)
        assert user.env == mock_env

    def test_model_cache_initialization(self, mock_env):
        """Test model cache is initialized."""
        user = TestUser(env=mock_env)
        assert isinstance(user._cache, dict)
        assert len(user._cache) == 0

    def test_model_ids_initialization(self, mock_env):
        """Test model IDs are initialized."""
        user = TestUser(env=mock_env)
        assert user._ids == ()

    def test_repr(self, mock_env):
        """Test string representation of model instance."""
        user = TestUser(env=mock_env)

        repr_str = repr(user)

        assert "TestUser" in repr_str

    def test_str(self, mock_env):
        """Test string conversion of model instance."""
        user = TestUser(env=mock_env)

        str_repr = str(user)

        assert "TestUser" in str_repr
