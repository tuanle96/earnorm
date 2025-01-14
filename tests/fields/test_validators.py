"""Test field validation."""

import pytest

from earnorm import fields
from earnorm.validators import ValidationError


def test_string_field_validation():
    """Test string field validation."""
    # Test required
    field = fields.String(required=True)
    field.name = "test"
    with pytest.raises(ValidationError, match="Field test is required"):
        field.validate(None)

    # Test min_length
    field = fields.String(min_length=3)
    field.name = "test"
    with pytest.raises(ValidationError, match="Length must be at least 3"):
        field.validate("ab")
    field.validate("abc")  # Should pass

    # Test max_length
    field = fields.String(max_length=5)
    field.name = "test"
    with pytest.raises(ValidationError, match="Length must be at most 5"):
        field.validate("123456")
    field.validate("12345")  # Should pass

    # Test pattern
    field = fields.String(pattern=r"^[A-Z]+$")
    field.name = "test"
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("abc")
    field.validate("ABC")  # Should pass

    # Test strip
    field = fields.String(strip=True)
    assert field.convert("  abc  ") == "abc"
    field = fields.String(strip=False)
    assert field.convert("  abc  ") == "  abc  "


def test_email_field_validation():
    """Test email field validation."""
    field = fields.Email()
    field.name = "email"

    # Test invalid email
    with pytest.raises(ValidationError, match="Invalid email address"):
        field.validate("invalid-email")

    # Test valid emails
    field.validate("test@example.com")
    field.validate("user.name+tag@example.co.uk")


def test_phone_field_validation():
    """Test phone field validation."""
    field = fields.Phone()
    field.name = "phone"

    # Test invalid phone numbers
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("123")  # Too short
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("abc")  # Invalid characters

    # Test valid phone numbers (E.164 format)
    field.validate("+84123456789")
    field.validate("84123456789")


def test_password_field_validation():
    """Test password field validation."""
    field = fields.Password()
    field.name = "password"

    # Test min length
    with pytest.raises(ValidationError, match="Length must be at least 8"):
        field.validate("Abc1@")

    # Test password requirements
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("password")  # Missing uppercase, digit, special char
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("Password")  # Missing digit, special char
    with pytest.raises(ValidationError, match="Value does not match pattern"):
        field.validate("Password1")  # Missing special char

    # Test valid password
    field.validate("Password1@")


def test_integer_field_validation():
    """Test integer field validation."""
    # Test min_value
    field = fields.Int(min_value=0)
    field.name = "age"
    with pytest.raises(ValidationError, match="Value must be at least 0"):
        field.validate(-1)
    field.validate(0)  # Should pass

    # Test max_value
    field = fields.Int(max_value=100)
    field.name = "percentage"
    with pytest.raises(ValidationError, match="Value must be at most 100"):
        field.validate(101)
    field.validate(100)  # Should pass

    # Test range
    field = fields.Int(min_value=0, max_value=100)
    field.name = "score"
    with pytest.raises(ValidationError):
        field.validate(-1)
    with pytest.raises(ValidationError):
        field.validate(101)
    field.validate(50)  # Should pass


def test_float_field_validation():
    """Test float field validation."""
    # Test min_value
    field = fields.Float(min_value=0.0)
    field.name = "price"
    with pytest.raises(ValidationError, match="Value must be at least 0.0"):
        field.validate(-0.1)
    field.validate(0.0)  # Should pass

    # Test max_value
    field = fields.Float(max_value=1.0)
    field.name = "ratio"
    with pytest.raises(ValidationError, match="Value must be at most 1.0"):
        field.validate(1.1)
    field.validate(1.0)  # Should pass

    # Test range
    field = fields.Float(min_value=0.0, max_value=1.0)
    field.name = "probability"
    with pytest.raises(ValidationError):
        field.validate(-0.1)
    with pytest.raises(ValidationError):
        field.validate(1.1)
    field.validate(0.5)  # Should pass
