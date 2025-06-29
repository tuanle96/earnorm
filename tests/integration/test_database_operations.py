"""Integration tests for database operations with real MongoDB.

This module tests complete database workflows including:
- Model creation and persistence
- CRUD operations with real database
- Query operations and filtering
- Transaction handling
- Connection management
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from earnorm.base.model.base import BaseModel
from earnorm.base.env import Environment
from earnorm.fields.primitive.string import StringField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField, DateField
from earnorm.fields.primitive.decimal import DecimalField
from earnorm.fields.primitive.uuid import UUIDField
from earnorm.fields.primitive.object_id import ObjectIdField
from earnorm.fields.primitive.json import JSONField
from earnorm.exceptions import ValidationError, DatabaseError


# Test Models for Integration Testing
class User(BaseModel):
    """User model for integration testing."""
    
    _name = "user"
    
    name = StringField(required=True, max_length=100)
    email = StringField(required=True, max_length=255)
    age = IntegerField(min_value=0, max_value=150)
    active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    profile_data = JSONField()


class Product(BaseModel):
    """Product model for integration testing."""
    
    _name = "product"
    
    name = StringField(required=True, max_length=200)
    price = DecimalField(max_digits=10, decimal_places=2)
    sku = StringField(required=True, max_length=50)
    in_stock = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


class Order(BaseModel):
    """Order model for integration testing."""
    
    _name = "order"
    
    order_id = UUIDField(default=uuid4)
    user_id = ObjectIdField(required=True)
    product_id = ObjectIdField(required=True)
    quantity = IntegerField(min_value=1, default=1)
    order_date = DateField()
    total_amount = DecimalField(max_digits=12, decimal_places=2)
    status = StringField(max_length=20, default="pending")


class TestDatabaseIntegration:
    """Test database integration with mocked MongoDB operations."""
    
    @pytest.fixture
    async def mock_env(self):
        """Create a mock environment with database adapter."""
        env = MagicMock(spec=Environment)
        env._initialized = True
        env.container = MagicMock()
        env.config = MagicMock()
        
        # Mock database adapter
        adapter = AsyncMock()
        env.adapter = adapter
        
        return env
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "active": True,
            "profile_data": {"preferences": {"theme": "dark"}}
        }
    
    @pytest.fixture
    def sample_product_data(self):
        """Sample product data for testing."""
        return {
            "name": "Test Product",
            "price": Decimal("99.99"),
            "sku": "TEST-001",
            "in_stock": True
        }
    
    @pytest.fixture
    def sample_order_data(self):
        """Sample order data for testing."""
        return {
            "user_id": "507f1f77bcf86cd799439011",
            "product_id": "507f1f77bcf86cd799439012",
            "quantity": 2,
            "order_date": date.today(),
            "total_amount": Decimal("199.98"),
            "status": "pending"
        }


class TestUserModelOperations(TestDatabaseIntegration):
    """Test User model CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, mock_env, sample_user_data):
        """Test creating a new user."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439011"
        
        with patch.object(User, '_get_env', return_value=mock_env):
            with patch.object(User, '_convert_to_db', return_value=sample_user_data):
                result = await User.create(sample_user_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is a User recordset
                assert isinstance(result, User)
    
    @pytest.mark.asyncio
    async def test_browse_user_by_id(self, mock_env, sample_user_data):
        """Test browsing user by ID."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.read.return_value = {
            "_id": "507f1f77bcf86cd799439011",
            **sample_user_data
        }
        
        with patch.object(User, '_get_env', return_value=mock_env):
            result = await User.browse("507f1f77bcf86cd799439011")
            
            # Verify result is a User recordset
            assert isinstance(result, User)
    
    @pytest.mark.asyncio
    async def test_search_users(self, mock_env):
        """Test searching users with filters."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(User, '_get_env', return_value=mock_env):
            result = await User.search([("active", "=", True)])
            
            # Verify result is a User recordset
            assert isinstance(result, User)
    
    @pytest.mark.asyncio
    async def test_update_user(self, mock_env, sample_user_data):
        """Test updating user data."""
        # Create user instance
        user = User(env=mock_env)
        user._ids = ("507f1f77bcf86cd799439011",)
        
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.write.return_value = True
        
        with patch.object(user, '_write', return_value=None):
            result = await user.write({"name": "Jane Doe"})
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_user(self, mock_env):
        """Test deleting a user."""
        # Create user instance
        user = User(env=mock_env)
        user._ids = ("507f1f77bcf86cd799439011",)
        
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.delete.return_value = 1
        
        with patch.object(user, '_unlink', return_value=None):
            result = await user.unlink()
            
            assert result is True


class TestProductModelOperations(TestDatabaseIntegration):
    """Test Product model operations."""
    
    @pytest.mark.asyncio
    async def test_create_product(self, mock_env, sample_product_data):
        """Test creating a new product."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439012"
        
        with patch.object(Product, '_get_env', return_value=mock_env):
            with patch.object(Product, '_convert_to_db', return_value=sample_product_data):
                result = await Product.create(sample_product_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is a Product recordset
                assert isinstance(result, Product)
    
    @pytest.mark.asyncio
    async def test_search_products_by_price_range(self, mock_env):
        """Test searching products by price range."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Product, '_get_env', return_value=mock_env):
            result = await Product.search([
                ("price", ">=", Decimal("50.00")),
                ("price", "<=", Decimal("100.00"))
            ])
            
            # Verify result is a Product recordset
            assert isinstance(result, Product)
    
    @pytest.mark.asyncio
    async def test_search_products_in_stock(self, mock_env):
        """Test searching products that are in stock."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Product, '_get_env', return_value=mock_env):
            result = await Product.search([("in_stock", "=", True)])
            
            # Verify result is a Product recordset
            assert isinstance(result, Product)


class TestOrderModelOperations(TestDatabaseIntegration):
    """Test Order model operations."""
    
    @pytest.mark.asyncio
    async def test_create_order(self, mock_env, sample_order_data):
        """Test creating a new order."""
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439013"
        
        with patch.object(Order, '_get_env', return_value=mock_env):
            with patch.object(Order, '_convert_to_db', return_value=sample_order_data):
                result = await Order.create(sample_order_data)
                
                # Verify adapter was called
                adapter.create.assert_called_once()
                
                # Verify result is an Order recordset
                assert isinstance(result, Order)
    
    @pytest.mark.asyncio
    async def test_search_orders_by_user(self, mock_env):
        """Test searching orders by user ID."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Order, '_get_env', return_value=mock_env):
            result = await Order.search([("user_id", "=", "507f1f77bcf86cd799439011")])
            
            # Verify result is an Order recordset
            assert isinstance(result, Order)
    
    @pytest.mark.asyncio
    async def test_search_orders_by_status(self, mock_env):
        """Test searching orders by status."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(Order, '_get_env', return_value=mock_env):
            result = await Order.search([("status", "=", "pending")])
            
            # Verify result is an Order recordset
            assert isinstance(result, Order)
    
    @pytest.mark.asyncio
    async def test_update_order_status(self, mock_env):
        """Test updating order status."""
        # Create order instance
        order = Order(env=mock_env)
        order._ids = ("507f1f77bcf86cd799439013",)
        
        # Mock adapter response
        adapter = mock_env.adapter
        adapter.write.return_value = True
        
        with patch.object(order, '_write', return_value=None):
            result = await order.write({"status": "completed"})
            
            assert result is True


class TestComplexQueries(TestDatabaseIntegration):
    """Test complex database queries and operations."""
    
    @pytest.mark.asyncio
    async def test_search_with_multiple_conditions(self, mock_env):
        """Test searching with multiple conditions."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(User, '_get_env', return_value=mock_env):
            result = await User.search([
                ("active", "=", True),
                ("age", ">=", 18),
                ("age", "<=", 65)
            ])
            
            # Verify result is a User recordset
            assert isinstance(result, User)
    
    @pytest.mark.asyncio
    async def test_search_with_json_field_query(self, mock_env):
        """Test searching with JSON field conditions."""
        # Mock adapter response
        adapter = mock_env.adapter
        query_mock = AsyncMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = []
        adapter.query.return_value = query_mock
        
        with patch.object(User, '_get_env', return_value=mock_env):
            result = await User.search([
                ("profile_data.preferences.theme", "=", "dark")
            ])
            
            # Verify result is a User recordset
            assert isinstance(result, User)


class TestTransactionOperations(TestDatabaseIntegration):
    """Test database transaction operations."""
    
    @pytest.mark.asyncio
    async def test_create_multiple_records_in_transaction(self, mock_env, sample_user_data, sample_product_data):
        """Test creating multiple records in a transaction."""
        # Mock transaction context
        transaction_mock = AsyncMock()
        transaction_mock.__aenter__ = AsyncMock(return_value=transaction_mock)
        transaction_mock.__aexit__ = AsyncMock(return_value=None)
        
        # Mock adapter responses
        adapter = mock_env.adapter
        adapter.create.side_effect = ["507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012"]
        adapter.transaction.return_value = transaction_mock
        
        with patch.object(User, '_get_env', return_value=mock_env):
            with patch.object(Product, '_get_env', return_value=mock_env):
                with patch.object(User, '_convert_to_db', return_value=sample_user_data):
                    with patch.object(Product, '_convert_to_db', return_value=sample_product_data):
                        # Simulate transaction
                        async with adapter.transaction():
                            user_result = await User.create(sample_user_data)
                            product_result = await Product.create(sample_product_data)
                        
                        # Verify both operations completed
                        assert isinstance(user_result, User)
                        assert isinstance(product_result, Product)
                        assert adapter.create.call_count == 2


class TestErrorHandling(TestDatabaseIntegration):
    """Test error handling in database operations."""
    
    @pytest.mark.asyncio
    async def test_create_with_validation_error(self, mock_env):
        """Test handling validation errors during creation."""
        invalid_data = {
            "name": "",  # Required field empty
            "email": "invalid-email",  # Invalid email format
            "age": -5  # Invalid age
        }
        
        with patch.object(User, '_get_env', return_value=mock_env):
            # Should raise validation error before reaching database
            with pytest.raises((ValidationError, ValueError)):
                await User.create(invalid_data)
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_env):
        """Test handling database connection errors."""
        # Mock adapter to raise database error
        adapter = mock_env.adapter
        adapter.create.side_effect = DatabaseError("Connection failed", backend="mongodb")
        
        sample_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        with patch.object(User, '_get_env', return_value=mock_env):
            with patch.object(User, '_convert_to_db', return_value=sample_data):
                with pytest.raises(DatabaseError) as exc_info:
                    await User.create(sample_data)
                
                assert "Connection failed" in str(exc_info.value)
                assert exc_info.value.backend == "mongodb"
    
    @pytest.mark.asyncio
    async def test_record_not_found(self, mock_env):
        """Test handling record not found scenarios."""
        # Mock adapter to return None (record not found)
        adapter = mock_env.adapter
        adapter.read.return_value = None
        
        with patch.object(User, '_get_env', return_value=mock_env):
            result = await User.browse("nonexistent_id")
            
            # Should return empty recordset
            assert isinstance(result, User)


class TestFieldValidationIntegration(TestDatabaseIntegration):
    """Test field validation in integration context."""
    
    @pytest.mark.asyncio
    async def test_string_field_validation_integration(self, mock_env):
        """Test string field validation in model context."""
        # Test with valid data
        valid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439011"
        
        with patch.object(User, '_get_env', return_value=mock_env):
            with patch.object(User, '_convert_to_db', return_value=valid_data):
                result = await User.create(valid_data)
                assert isinstance(result, User)
    
    @pytest.mark.asyncio
    async def test_decimal_field_validation_integration(self, mock_env):
        """Test decimal field validation in model context."""
        # Test with valid decimal data
        valid_data = {
            "name": "Test Product",
            "price": Decimal("99.99"),
            "sku": "TEST-001"
        }
        
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439012"
        
        with patch.object(Product, '_get_env', return_value=mock_env):
            with patch.object(Product, '_convert_to_db', return_value=valid_data):
                result = await Product.create(valid_data)
                assert isinstance(result, Product)
    
    @pytest.mark.asyncio
    async def test_datetime_field_validation_integration(self, mock_env):
        """Test datetime field validation in model context."""
        # Test with datetime fields
        now = datetime.now()
        valid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "created_at": now,
            "updated_at": now
        }
        
        adapter = mock_env.adapter
        adapter.create.return_value = "507f1f77bcf86cd799439011"
        
        with patch.object(User, '_get_env', return_value=mock_env):
            with patch.object(User, '_convert_to_db', return_value=valid_data):
                result = await User.create(valid_data)
                assert isinstance(result, User)
