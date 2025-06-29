"""Relation fields for EarnORM.

This package provides relation field implementations including:
1. One-to-one relations
2. Many-to-one relations
3. One-to-many relations
4. Many-to-many relations

Examples:
    >>> from earnorm.fields.relations import (
    ...     OneToOneField,
    ...     ManyToOneField,
    ...     OneToManyField,
    ...     ManyToManyField
    ... )
    >>> from earnorm.base.model import BaseModel

    >>> class User(BaseModel):
    ...     _name = 'res.user'
    ...     profile = OneToOneField('Profile', related_name='user')
    ...     department = ManyToOneField('Department', related_name='employees')
    ...     posts = OneToManyField('Post', related_name='author')
    ...     roles = ManyToManyField('Role', related_name='users')
"""

from earnorm.fields.relations.base import RelationField
from earnorm.fields.relations.many_to_many import ManyToManyField
from earnorm.fields.relations.many_to_one import ManyToOneField
from earnorm.fields.relations.one_to_many import OneToManyField
from earnorm.fields.relations.one_to_one import OneToOneField
from earnorm.types.relations import RelationType

__all__ = [
    "ManyToManyField",
    "ManyToOneField",
    "OneToManyField",
    "OneToOneField",
    "RelationField",
    "RelationType",
]
