"""Basic functionality tests to verify test infrastructure.

This module contains simple tests to verify that the test infrastructure
is working correctly and can import EarnORM modules.
"""

import pytest
from typing import Any

# Test basic imports
def test_import_earnorm():
    """Test that we can import the main earnorm module."""
    import earnorm
    assert earnorm is not None


def test_import_fields():
    """Test that we can import field modules."""
    from earnorm.fields.primitive.string import StringField
    from earnorm.fields.primitive.number import IntegerField
    from earnorm.fields.primitive.boolean import BooleanField
    
    assert StringField is not None
    assert IntegerField is not None
    assert BooleanField is not None


def test_import_exceptions():
    """Test that we can import exception classes."""
    from earnorm.exceptions import ValidationError, EarnORMError, DatabaseError
    
    assert ValidationError is not None
    assert EarnORMError is not None
    assert DatabaseError is not None


def test_create_string_field():
    """Test creating a basic string field."""
    from earnorm.fields.primitive.string import StringField
    
    field = StringField()
    assert field is not None
    assert isinstance(field, StringField)


def test_create_integer_field():
    """Test creating a basic integer field."""
    from earnorm.fields.primitive.number import IntegerField
    
    field = IntegerField()
    assert field is not None
    assert isinstance(field, IntegerField)


def test_create_boolean_field():
    """Test creating a basic boolean field."""
    from earnorm.fields.primitive.boolean import BooleanField
    
    field = BooleanField()
    assert field is not None
    assert isinstance(field, BooleanField)


def test_validation_error_creation():
    """Test creating ValidationError instances."""
    from earnorm.exceptions import ValidationError

    error = ValidationError(
        message="Test error",
        field_name="test_field",
        code="validation_failed"
    )

    assert error.message == "Test error"
    assert error.field_name == "test_field"
    assert error.code == "validation_failed"


def test_database_error_creation():
    """Test creating DatabaseError instances."""
    from earnorm.exceptions import DatabaseError
    
    error = DatabaseError("Test database error", backend="mongodb")
    
    assert "Test database error" in str(error)
    assert error.backend == "mongodb"


@pytest.mark.asyncio
async def test_async_test_support():
    """Test that async tests work correctly."""
    import asyncio
    
    # Simple async operation
    await asyncio.sleep(0.001)
    
    # Verify we can use async/await
    async def dummy_async_function():
        return "async_result"
    
    result = await dummy_async_function()
    assert result == "async_result"


def test_pytest_fixtures_work(sample_data):
    """Test that pytest fixtures from conftest.py work."""
    assert sample_data is not None
    assert isinstance(sample_data, dict)
    assert "name" in sample_data
    assert "email" in sample_data


def test_sample_data_list_fixture(sample_data_list):
    """Test that sample data list fixture works."""
    assert sample_data_list is not None
    assert isinstance(sample_data_list, list)
    assert len(sample_data_list) > 0
    assert all(isinstance(item, dict) for item in sample_data_list)


@pytest.mark.unit
def test_unit_marker():
    """Test that unit test marker works."""
    assert True


class TestBasicMath:
    """Test class to verify test class structure works."""
    
    def test_addition(self):
        """Test basic addition."""
        assert 1 + 1 == 2
    
    def test_subtraction(self):
        """Test basic subtraction."""
        assert 5 - 3 == 2
    
    def test_multiplication(self):
        """Test basic multiplication."""
        assert 3 * 4 == 12
    
    def test_division(self):
        """Test basic division."""
        assert 10 / 2 == 5


class TestStringOperations:
    """Test class for string operations."""
    
    def test_string_concatenation(self):
        """Test string concatenation."""
        result = "Hello" + " " + "World"
        assert result == "Hello World"
    
    def test_string_formatting(self):
        """Test string formatting."""
        name = "EarnORM"
        result = f"Welcome to {name}!"
        assert result == "Welcome to EarnORM!"
    
    def test_string_methods(self):
        """Test string methods."""
        text = "  EarnORM Test  "
        assert text.strip() == "EarnORM Test"
        assert text.lower().strip() == "earnorm test"
        assert text.upper().strip() == "EARNORM TEST"


class TestListOperations:
    """Test class for list operations."""
    
    def test_list_creation(self):
        """Test list creation."""
        items = [1, 2, 3, 4, 5]
        assert len(items) == 5
        assert items[0] == 1
        assert items[-1] == 5
    
    def test_list_methods(self):
        """Test list methods."""
        items = [1, 2, 3]
        items.append(4)
        assert len(items) == 4
        assert 4 in items
        
        items.remove(2)
        assert 2 not in items
        assert len(items) == 3
    
    def test_list_comprehension(self):
        """Test list comprehension."""
        numbers = [1, 2, 3, 4, 5]
        squares = [x * x for x in numbers]
        expected = [1, 4, 9, 16, 25]
        assert squares == expected


class TestDictOperations:
    """Test class for dictionary operations."""
    
    def test_dict_creation(self):
        """Test dictionary creation."""
        data = {"name": "Test", "age": 25}
        assert data["name"] == "Test"
        assert data["age"] == 25
    
    def test_dict_methods(self):
        """Test dictionary methods."""
        data = {"a": 1, "b": 2}
        assert "a" in data
        assert "c" not in data
        
        data["c"] = 3
        assert "c" in data
        assert len(data) == 3
    
    def test_dict_get_method(self):
        """Test dictionary get method."""
        data = {"name": "Test"}
        assert data.get("name") == "Test"
        assert data.get("age") is None
        assert data.get("age", 0) == 0


def test_exception_handling():
    """Test exception handling."""
    with pytest.raises(ValueError):
        int("not_a_number")
    
    with pytest.raises(KeyError):
        data = {"a": 1}
        _ = data["b"]
    
    with pytest.raises(IndexError):
        items = [1, 2, 3]
        _ = items[10]


def test_type_checking():
    """Test type checking functions."""
    assert isinstance("hello", str)
    assert isinstance(42, int)
    assert isinstance(3.14, float)
    assert isinstance(True, bool)
    assert isinstance([1, 2, 3], list)
    assert isinstance({"a": 1}, dict)


def test_none_values():
    """Test handling of None values."""
    value = None
    assert value is None
    assert value != False
    assert value != 0
    assert value != ""
    assert value != []


def test_boolean_logic():
    """Test boolean logic operations."""
    assert True and True
    assert not (True and False)
    assert True or False
    assert not (False or False)
    
    # Test truthiness
    assert bool("non-empty string")
    assert not bool("")
    assert bool([1, 2, 3])
    assert not bool([])
    assert bool({"a": 1})
    assert not bool({})


@pytest.mark.parametrize("input_value,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (4, 8),
    (5, 10),
])
def test_parametrized_double(input_value: int, expected: int):
    """Test parametrized test for doubling numbers."""
    result = input_value * 2
    assert result == expected


@pytest.mark.parametrize("text,expected_length", [
    ("hello", 5),
    ("world", 5),
    ("EarnORM", 7),
    ("", 0),
    ("a", 1),
])
def test_parametrized_string_length(text: str, expected_length: int):
    """Test parametrized test for string lengths."""
    assert len(text) == expected_length
