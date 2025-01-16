"""Relationships module for EarnORM.

This module provides classes for managing model relationships:
- Relationship definitions (many2one, one2many, many2many)
- Relationship loading and cascading
"""

from earnorm.base.relationships.manager import Relationship, RelationshipManager

__all__ = ["Relationship", "RelationshipManager"]
