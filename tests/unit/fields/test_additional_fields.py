"""Additional field tests for comprehensive coverage.

This module tests additional field types and advanced functionality
to expand test coverage beyond the basic field tests.
"""

import pytest
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID, uuid4

from earnorm.fields.primitive.datetime import DateTimeField, DateField, TimeField
from earnorm.fields.primitive.decimal import DecimalField
from earnorm.fields.primitive.uuid import UUIDField
from earnorm.fields.primitive.object_id import ObjectIdField
from earnorm.fields.primitive.json import JSONField
from earnorm.exceptions import ValidationError, FieldValidationError


class TestDateTimeFields:
    """Test DateTime, Date, and Time field functionality."""
    
    def test_create_datetime_field(self):
        """Test creating a datetime field."""
        field = DateTimeField()
        
        assert isinstance(field, DateTimeField)
        assert field.required is False
        assert field.auto_now is False
        assert field.auto_now_add is False
    
    def test_create_datetime_field_with_auto_now(self):
        """Test creating datetime field with auto_now."""
        field = DateTimeField(auto_now=True)
        
        assert field.auto_now is True
        assert field.auto_now_add is False
    
    def test_create_datetime_field_with_auto_now_add(self):
        """Test creating datetime field with auto_now_add."""
        field = DateTimeField(auto_now_add=True)
        
        assert field.auto_now is False
        assert field.auto_now_add is True
    
    @pytest.mark.asyncio
    async def test_datetime_field_validate_datetime(self):
        """Test datetime field validates datetime objects."""
        field = DateTimeField()
        now = datetime.now()

        result = await field.validate(now)

        # DateTimeField may add timezone info
        assert isinstance(result, datetime)
        assert result.year == now.year
        assert result.month == now.month
        assert result.day == now.day
    
    @pytest.mark.asyncio
    async def test_datetime_field_convert_string(self):
        """Test datetime field converts ISO string to datetime."""
        field = DateTimeField()
        iso_string = "2023-12-25T10:30:00"
        
        result = await field.convert(iso_string)
        
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
    
    def test_create_date_field(self):
        """Test creating a date field."""
        field = DateField()
        
        assert isinstance(field, DateField)
        assert field.required is False
    
    @pytest.mark.asyncio
    async def test_date_field_validate_date(self):
        """Test date field validates date objects."""
        field = DateField()
        # DateField expects datetime objects, not date objects
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await field.validate(today)

        assert isinstance(result, datetime)
        assert result.year == today.year
        assert result.month == today.month
        assert result.day == today.day
    
    def test_create_time_field(self):
        """Test creating a time field."""
        field = TimeField()
        
        assert isinstance(field, TimeField)
        assert field.required is False
    
    @pytest.mark.asyncio
    async def test_time_field_validate_time(self):
        """Test time field validates time objects."""
        field = TimeField()
        now_time = time(10, 30, 45)
        
        result = await field.validate(now_time)
        
        assert result == now_time
        assert isinstance(result, time)


class TestDecimalField:
    """Test DecimalField functionality."""
    
    def test_create_decimal_field(self):
        """Test creating a decimal field."""
        field = DecimalField()

        assert isinstance(field, DecimalField)
        assert field.required is False
        # DecimalField has default values for max_digits and decimal_places
        assert field.max_digits == 65  # Default value
        assert field.decimal_places == 30  # Default value
    
    def test_create_decimal_field_with_constraints(self):
        """Test creating decimal field with constraints."""
        field = DecimalField(max_digits=10, decimal_places=2)
        
        assert field.max_digits == 10
        assert field.decimal_places == 2
    
    @pytest.mark.asyncio
    async def test_decimal_field_validate_decimal(self):
        """Test decimal field validates Decimal objects."""
        field = DecimalField()
        value = Decimal("123.45")
        
        result = await field.validate(value)
        
        assert result == value
        assert isinstance(result, Decimal)
    
    @pytest.mark.asyncio
    async def test_decimal_field_convert_string(self):
        """Test decimal field converts string to Decimal."""
        field = DecimalField()
        
        result = await field.convert("123.45")
        
        assert result == Decimal("123.45")
        assert isinstance(result, Decimal)
    
    @pytest.mark.asyncio
    async def test_decimal_field_convert_float(self):
        """Test decimal field converts float to Decimal."""
        field = DecimalField()
        
        result = await field.convert(123.45)
        
        assert isinstance(result, Decimal)
        assert float(result) == 123.45


class TestUUIDField:
    """Test UUIDField functionality."""
    
    def test_create_uuid_field(self):
        """Test creating a UUID field."""
        field = UUIDField()

        assert isinstance(field, UUIDField)
        assert field.required is False
        # UUIDField has default version 4
        assert field.version == 4
    
    def test_create_uuid_field_with_version(self):
        """Test creating UUID field with specific version."""
        field = UUIDField(version=4)
        
        assert field.version == 4
    
    @pytest.mark.asyncio
    async def test_uuid_field_validate_uuid(self):
        """Test UUID field validates UUID objects."""
        field = UUIDField()
        uuid_value = uuid4()
        
        result = await field.validate(uuid_value)
        
        assert result == uuid_value
        assert isinstance(result, UUID)
    
    @pytest.mark.asyncio
    async def test_uuid_field_convert_string(self):
        """Test UUID field converts string to UUID."""
        field = UUIDField()
        uuid_string = "550e8400-e29b-41d4-a716-446655440000"
        
        result = await field.convert(uuid_string)
        
        assert isinstance(result, UUID)
        assert str(result) == uuid_string


class TestObjectIdField:
    """Test ObjectIdField functionality."""
    
    def test_create_object_id_field(self):
        """Test creating an ObjectId field."""
        field = ObjectIdField()
        
        assert isinstance(field, ObjectIdField)
        assert field.required is False
    
    @pytest.mark.asyncio
    async def test_object_id_field_convert_string(self):
        """Test ObjectId field converts string to ObjectId."""
        field = ObjectIdField()
        oid_string = "507f1f77bcf86cd799439011"
        
        result = await field.convert(oid_string)
        
        # Result should be a valid ObjectId representation
        assert result is not None
        assert len(str(result)) == 24


class TestJSONField:
    """Test JSONField functionality."""
    
    def test_create_json_field(self):
        """Test creating a JSON field."""
        field = JSONField()
        
        assert isinstance(field, JSONField)
        assert field.required is False
    
    @pytest.mark.asyncio
    async def test_json_field_validate_dict(self):
        """Test JSON field validates dictionary objects."""
        field = JSONField()
        data = {"key": "value", "number": 42}
        
        result = await field.validate(data)
        
        assert result == data
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_json_field_validate_list(self):
        """Test JSON field validates list objects."""
        field = JSONField()
        data = [1, 2, 3, "test"]
        
        result = await field.validate(data)
        
        assert result == data
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_json_field_convert_string(self):
        """Test JSON field converts JSON string to object."""
        field = JSONField()
        json_string = '{"key": "value", "number": 42}'
        
        result = await field.convert(json_string)
        
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42


class TestFieldDatabaseOperations:
    """Test field database operations for additional fields."""
    
    @pytest.mark.asyncio
    async def test_datetime_field_to_db(self):
        """Test datetime field database serialization."""
        field = DateTimeField()
        now = datetime.now()

        result = await field.to_db(now, "mongodb")

        # DateTime is serialized to ISO string for MongoDB
        assert isinstance(result, str)
        assert "T" in result  # ISO format contains T
    
    @pytest.mark.asyncio
    async def test_datetime_field_from_db(self):
        """Test datetime field database deserialization."""
        field = DateTimeField()
        now = datetime.now()

        result = await field.from_db(now, "mongodb")

        # DateTime from DB may have timezone info added
        assert isinstance(result, datetime)
        assert result.year == now.year
        assert result.month == now.month
        assert result.day == now.day
    
    @pytest.mark.asyncio
    async def test_decimal_field_to_db(self):
        """Test decimal field database serialization."""
        field = DecimalField(decimal_places=2)  # Specify decimal places to avoid quantize error
        value = Decimal("123.45")

        result = await field.to_db(value, "mongodb")

        # MongoDB typically stores decimals as strings or floats
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_uuid_field_to_db(self):
        """Test UUID field database serialization."""
        field = UUIDField()
        uuid_value = uuid4()
        
        result = await field.to_db(uuid_value, "mongodb")
        
        # UUID is typically stored as string in MongoDB
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_json_field_to_db(self):
        """Test JSON field database serialization."""
        field = JSONField()
        data = {"key": "value", "number": 42}
        
        result = await field.to_db(data, "mongodb")
        
        assert result == data


class TestFieldEdgeCases:
    """Test edge cases and error conditions for additional fields."""
    
    @pytest.mark.asyncio
    async def test_datetime_field_none_optional(self):
        """Test datetime field with None value when optional."""
        field = DateTimeField(required=False)
        
        result = await field.validate(None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_decimal_field_none_optional(self):
        """Test decimal field with None value when optional."""
        field = DecimalField(required=False)
        
        result = await field.validate(None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_uuid_field_none_optional(self):
        """Test UUID field with None value when optional."""
        field = UUIDField(required=False)
        
        result = await field.validate(None)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_json_field_none_optional(self):
        """Test JSON field with None value when optional."""
        field = JSONField(required=False)
        
        result = await field.validate(None)
        
        assert result is None
    
    def test_field_repr_methods(self):
        """Test string representation of additional fields."""
        datetime_field = DateTimeField(required=True, auto_now=True)
        decimal_field = DecimalField(max_digits=10, decimal_places=2)
        uuid_field = UUIDField(version=4)
        json_field = JSONField()
        
        # Should not raise exceptions
        assert "DateTimeField" in repr(datetime_field)
        assert "DecimalField" in repr(decimal_field)
        assert "UUIDField" in repr(uuid_field)
        assert "JSONField" in repr(json_field)


class TestFieldProperties:
    """Test field property access for additional fields."""
    
    def test_datetime_field_properties(self):
        """Test datetime field properties."""
        field = DateTimeField(required=True, auto_now=True)
        
        assert field.required is True
        assert field.auto_now is True
        assert hasattr(field, 'field_type')
        assert hasattr(field, 'python_type')
    
    def test_decimal_field_properties(self):
        """Test decimal field properties."""
        field = DecimalField(required=True, max_digits=10, decimal_places=2)
        
        assert field.required is True
        assert field.max_digits == 10
        assert field.decimal_places == 2
        assert hasattr(field, 'field_type')
        assert hasattr(field, 'python_type')
    
    def test_uuid_field_properties(self):
        """Test UUID field properties."""
        field = UUIDField(required=True, version=4)
        
        assert field.required is True
        assert field.version == 4
        assert hasattr(field, 'field_type')
        assert hasattr(field, 'python_type')
    
    def test_json_field_properties(self):
        """Test JSON field properties."""
        field = JSONField(required=True)
        
        assert field.required is True
        assert hasattr(field, 'field_type')
        assert hasattr(field, 'python_type')
