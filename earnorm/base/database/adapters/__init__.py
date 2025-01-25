"""Database adapter implementations.

This module provides adapter implementations for different database backends.
Currently supports:
- MongoDB
"""

from .mongo import MongoAdapter

__all__ = ["MongoAdapter"]
