"""Simple example models."""

from earnorm import BaseModel, Email, Int, String


class User(BaseModel):
    """User model."""

    # Collection configuration
    _collection = "users"
    _name = "user"  # Model name
    _indexes = [{"email": 1}]  # MongoDB index format
    _abstract = False
    _acl = {}
    _rules = {}
    _events = {}
    _audit = {}
    _cache = {}
    _metrics = {}

    # Fields
    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)
