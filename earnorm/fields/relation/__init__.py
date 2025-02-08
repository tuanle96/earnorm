"""Relation field types.

This module provides field types for database relationships:
- OneToManyField: One-to-many relationship
- ManyToOneField: Many-to-one relationship
- ManyToManyField: Many-to-many relationship
"""

from earnorm.fields.relation.base import RelationField
from earnorm.fields.relation.many_to_many import ManyToManyField
from earnorm.fields.relation.many_to_one import ManyToOneField
from earnorm.fields.relation.one_to_many import OneToManyField
from earnorm.fields.relation.one_to_one import OneToOneField

__all__ = [
    "RelationField",
    "OneToOneField",
    "OneToManyField",
    "ManyToOneField",
    "ManyToManyField",
]
