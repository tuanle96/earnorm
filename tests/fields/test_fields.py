"""Test field types."""

import pytest
from bson import ObjectId

from earnorm import fields


def test_string_field():
    """Test string field."""
    field = fields.String()
    field.name = "test"

    # Test convert
    assert field.convert(None) == ""
    assert field.convert(123) == "123"
    assert field.convert("abc") == "abc"

    # Test to_mongo
    assert field.to_mongo(None) == ""
    assert field.to_mongo("abc") == "abc"

    # Test from_mongo
    assert field.from_mongo(None) == ""
    assert field.from_mongo("abc") == "abc"


def test_integer_field():
    """Test integer field."""
    field = fields.Int()
    field.name = "test"

    # Test convert
    assert field.convert(None) == 0
    assert field.convert("123") == 123
    assert field.convert(123) == 123
    assert field.convert(123.45) == 123

    # Test to_mongo
    assert field.to_mongo(None) == 0
    assert field.to_mongo(123) == 123

    # Test from_mongo
    assert field.from_mongo(None) == 0
    assert field.from_mongo(123) == 123


def test_float_field():
    """Test float field."""
    field = fields.Float()
    field.name = "test"

    # Test convert
    assert field.convert(None) == 0.0
    assert field.convert("123.45") == 123.45
    assert field.convert(123) == 123.0
    assert field.convert(123.45) == 123.45

    # Test to_mongo
    assert field.to_mongo(None) == 0.0
    assert field.to_mongo(123.45) == 123.45

    # Test from_mongo
    assert field.from_mongo(None) == 0.0
    assert field.from_mongo(123.45) == 123.45


def test_boolean_field():
    """Test boolean field."""
    field = fields.Bool()
    field.name = "test"

    # Test convert
    assert field.convert(None) is False
    assert field.convert(True) is True
    assert field.convert(False) is False
    assert field.convert(1) is True
    assert field.convert(0) is False
    assert field.convert("true") is True
    assert field.convert("") is False

    # Test to_mongo
    assert field.to_mongo(None) is False
    assert field.to_mongo(True) is True
    assert field.to_mongo(False) is False

    # Test from_mongo
    assert field.from_mongo(None) is False
    assert field.from_mongo(True) is True
    assert field.from_mongo(False) is False


def test_objectid_field():
    """Test ObjectId field."""
    field = fields.ObjectId()
    field.name = "test"

    # Test convert
    oid = ObjectId()
    assert isinstance(field.convert(None), ObjectId)
    assert field.convert(oid) == oid
    assert field.convert(str(oid)) == oid

    # Test to_dict
    assert field.to_dict(None) is None
    assert field.to_dict(oid) == str(oid)

    # Test to_mongo
    assert field.to_mongo(None) is None
    assert field.to_mongo(oid) == oid
    assert field.to_mongo(str(oid)) == oid

    # Test from_mongo
    assert isinstance(field.from_mongo(None), ObjectId)
    assert field.from_mongo(oid) == oid
    assert field.from_mongo(str(oid)) == oid


def test_list_field():
    """Test list field."""
    field = fields.List(fields.String())
    field.name = "test"

    # Test convert
    assert field.convert(None) == []
    assert field.convert(["a", "b", "c"]) == ["a", "b", "c"]
    with pytest.raises(ValueError, match="Expected list"):
        field.convert("not a list")

    # Test to_dict
    assert field.to_dict(None) is None
    assert field.to_dict(["a", "b", "c"]) == ["a", "b", "c"]

    # Test to_mongo
    assert field.to_mongo(None) is None
    assert field.to_mongo(["a", "b", "c"]) == ["a", "b", "c"]

    # Test from_mongo
    assert field.from_mongo(None) == []
    assert field.from_mongo(["a", "b", "c"]) == ["a", "b", "c"]
    with pytest.raises(ValueError, match="Expected list"):
        field.from_mongo("not a list")


def test_dict_field():
    """Test dict field."""
    field = fields.Dict()
    field.name = "test"

    # Test convert
    assert field.convert(None) == {}
    assert field.convert({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    # Test to_mongo
    assert field.to_mongo(None) == {}
    assert field.to_mongo({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    # Test from_mongo
    assert field.from_mongo(None) == {}
    assert field.from_mongo({"a": 1, "b": 2}) == {"a": 1, "b": 2}
