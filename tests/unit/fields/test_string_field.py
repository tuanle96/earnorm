"""Unit tests for StringField class.

This module tests the StringField functionality including:
- Field creation and configuration
- Value validation and conversion
- String-specific validations (length, patterns, etc.)
- Database serialization/deserialization
"""

import pytest

from earnorm.fields.primitive.string import StringField
from earnorm.exceptions import ValidationError


class TestStringFieldCreation:
    """Test StringField creation and configuration."""

    def test_create_basic_string_field(self):
        """Test creating a basic string field."""
        field = StringField()

        assert isinstance(field, StringField)
        assert field.required is False
        assert field.max_length is None
        assert field.min_length is None

    def test_create_string_field_with_options(self):
        """Test creating string field with various options."""
        field = StringField(
            required=True,
            max_length=100,
            min_length=5
        )

        assert field.required is True
        assert field.max_length == 100
        assert field.min_length == 5
        # Validators are TypeValidator instances, not strings
        assert len(field.validators) > 0
        assert any(hasattr(v, 'expected_type') for v in field.validators)

    def test_create_string_field_with_regex_pattern(self):
        """Test creating string field with regex pattern."""
        pattern = r"^[A-Z][a-z]+$"
        field = StringField(pattern=pattern)

        assert field.pattern == pattern


class TestStringFieldValidation:
    """Test StringField validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_valid_string(self):
        """Test validation passes for valid string."""
        field = StringField(max_length=10, min_length=3)

        # Should not raise any exception
        result1 = await field.validate("hello")
        result2 = await field.validate("test")
        result3 = await field.validate("a" * 10)

        assert result1 == "hello"
        assert result2 == "test"
        assert result3 == "a" * 10

    @pytest.mark.asyncio
    async def test_validate_none_value_optional_field(self):
        """Test validation passes for None value in optional field."""
        field = StringField(required=False)

        # Should not raise any exception
        result = await field.validate(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_none_value_required_field(self):
        """Test validation fails for None value in required field."""
        field = StringField(required=True)

        with pytest.raises(ValidationError) as exc_info:
            await field.validate(None)

        assert "required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_empty_string_required_field(self):
        """Test validation fails for empty string in required field."""
        field = StringField(required=True)

        with pytest.raises(ValidationError) as exc_info:
            await field.validate("")

        assert "required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_string_too_long(self):
        """Test validation fails for string exceeding max_length."""
        field = StringField(max_length=5)

        with pytest.raises(ValueError) as exc_info:
            await field.validate("toolong")

        assert "length" in str(exc_info.value).lower()
        assert "5" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_string_too_short(self):
        """Test validation fails for string below min_length."""
        field = StringField(min_length=5)

        with pytest.raises(ValueError) as exc_info:
            await field.validate("hi")

        assert "length" in str(exc_info.value).lower()
        assert "5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_validate_string_pattern_match(self):
        """Test validation passes for string matching pattern."""
        field = StringField(pattern=r"^[A-Z][a-z]+$")

        # Should not raise any exception
        result1 = await field.validate("Hello")
        result2 = await field.validate("World")

        assert result1 == "Hello"
        assert result2 == "World"

    @pytest.mark.asyncio
    async def test_validate_string_pattern_no_match(self):
        """Test validation fails for string not matching pattern."""
        field = StringField(pattern=r"^[A-Z][a-z]+$")

        with pytest.raises(ValueError) as exc_info:
            await field.validate("hello")  # lowercase first letter

        assert "pattern" in str(exc_info.value).lower()


class TestStringFieldConversion:
    """Test StringField value conversion functionality."""

    @pytest.mark.asyncio
    async def test_convert_string_value(self):
        """Test converting string value (no change expected)."""
        field = StringField()

        result = await field.convert("hello")

        assert result == "hello"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convert_none_value(self):
        """Test converting None value."""
        field = StringField()

        result = await field.convert(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_convert_integer_to_string(self):
        """Test converting integer to string."""
        field = StringField()

        result = await field.convert(123)

        assert result == "123"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convert_float_to_string(self):
        """Test converting float to string."""
        field = StringField()

        result = await field.convert(123.45)

        assert result == "123.45"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convert_boolean_to_string(self):
        """Test converting boolean to string."""
        field = StringField()

        result_true = await field.convert(True)
        result_false = await field.convert(False)

        assert result_true == "True"
        assert result_false == "False"
        assert isinstance(result_true, str)
        assert isinstance(result_false, str)


class TestStringFieldDatabaseOperations:
    """Test StringField database serialization/deserialization."""

    def test_to_db_string_value(self):
        """Test converting string value for database storage."""
        field = StringField()

        result = field.to_db("hello", "mongodb")

        assert result == "hello"
        assert isinstance(result, str)

    def test_to_db_none_value(self):
        """Test converting None value for database storage."""
        field = StringField()

        result = field.to_db(None, "mongodb")

        assert result is None

    def test_from_db_string_value(self):
        """Test converting string value from database."""
        field = StringField()

        result = field.from_db("hello", "mongodb")

        assert result == "hello"
        assert isinstance(result, str)

    def test_from_db_none_value(self):
        """Test converting None value from database."""
        field = StringField()

        result = field.from_db(None, "mongodb")

        assert result is None


class TestStringFieldDefaults:
    """Test StringField default value handling."""

    def test_field_without_default(self):
        """Test field without default value."""
        field = StringField()

        # Check that field doesn't have a default attribute or it's None
        assert not hasattr(field, 'default') or field.default is None

    def test_field_with_static_default(self):
        """Test field with static default value."""
        field = StringField(default="default_value")

        assert field.default == "default_value"

    def test_field_with_callable_default(self):
        """Test field with callable default value."""
        def get_default():
            return "dynamic_default"

        field = StringField(default=get_default)

        assert field.default == get_default
        assert field.default() == "dynamic_default"


class TestStringFieldEdgeCases:
    """Test StringField edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_validate_unicode_string(self):
        """Test validation with unicode characters."""
        field = StringField(max_length=10)

        # Should not raise any exception
        result1 = await field.validate("héllo")
        result2 = await field.validate("测试")
        result3 = await field.validate("🚀")

        assert result1 == "héllo"
        assert result2 == "测试"
        assert result3 == "🚀"

    @pytest.mark.asyncio
    async def test_validate_multiline_string(self):
        """Test validation with multiline strings."""
        field = StringField(max_length=20)

        multiline = "line1\nline2\nline3"

        # Should not raise any exception
        result = await field.validate(multiline)
        assert result == multiline

    def test_pattern_compilation_error(self):
        """Test handling of invalid regex pattern."""
        with pytest.raises(ValueError):
            StringField(pattern="[invalid regex")

    def test_field_repr(self):
        """Test string representation of field."""
        field = StringField(
            required=True,
            max_length=100
        )

        repr_str = repr(field)

        assert "StringField" in repr_str
