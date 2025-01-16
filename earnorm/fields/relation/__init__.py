"""Relation field types."""

from earnorm.fields.relation.base import BaseRelationField
from earnorm.fields.relation.many2many import Many2manyField
from earnorm.fields.relation.many2one import Many2oneField
from earnorm.fields.relation.one2many import One2manyField
from earnorm.fields.relation.reference import ReferenceField

__all__ = [
    "BaseRelationField",
    "ReferenceField",
    "Many2oneField",
    "One2manyField",
    "Many2manyField",
]
