"""Field types for EarnORM."""

from earnorm.fields.base import BooleanField as Bool
from earnorm.fields.base import DictField as Dict
from earnorm.fields.base import FloatField as Float
from earnorm.fields.base import IntegerField as Int
from earnorm.fields.base import ListField as List
from earnorm.fields.base import ObjectIdField as ObjectId
from earnorm.fields.relation import Many2manyField as Many2many
from earnorm.fields.relation import Many2oneField as Many2one
from earnorm.fields.relation import One2manyField as One2many
from earnorm.fields.string import EmailStringField as Email
from earnorm.fields.string import PasswordStringField as Password
from earnorm.fields.string import PhoneStringField as Phone
from earnorm.fields.string import StringField as String

__all__ = [
    # Base Fields
    "String",
    "Int",
    "Float",
    "Bool",
    "ObjectId",
    "List",
    "Dict",
    # String Fields
    "Email",
    "Phone",
    "Password",
    # Relation Fields
    "Many2one",
    "One2many",
    "Many2many",
]
