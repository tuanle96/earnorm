"""Relation field types.

This module provides field types for database relationships:
- OneToOneField: One-to-one relationship
- OneToManyField: One-to-many relationship
- ManyToOneField: Many-to-one relationship
- ManyToManyField: Many-to-many relationship
"""

from earnorm.fields.relation.many_to_many import ManyToManyField
from earnorm.fields.relation.many_to_one import ManyToOneField
from earnorm.fields.relation.one_to_many import OneToManyField

__all__ = [
    "OneToManyField",
    "ManyToOneField",
    "ManyToManyField",
]
