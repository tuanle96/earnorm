"""EarnORM - Async MongoDB ORM."""

from typing import Any, Type

from earnorm.base.model import BaseModel
from earnorm.di import Container, DIContainer
from earnorm.fields import BooleanField as Bool
from earnorm.fields import CharField as Char
from earnorm.fields import DictField as Dict
from earnorm.fields import EmailField as Email
from earnorm.fields import FloatField as Float
from earnorm.fields import IntegerField as Int
from earnorm.fields import ListField as List
from earnorm.fields import Many2manyField as Many2many
from earnorm.fields import Many2oneField as Many2one
from earnorm.fields import ObjectIdField as ObjectId
from earnorm.fields import One2manyField as One2many
from earnorm.fields import PasswordField as Password
from earnorm.fields import PhoneField as Phone
from earnorm.fields import ReferenceField as Reference
from earnorm.fields import StringField as String

# Global variables
env = None
registry = None
di = None

# Global container instance
container = DIContainer()


def get_all_subclasses(cls: Type[BaseModel]) -> list[Type[BaseModel]]:
    """Get all subclasses of a class recursively.

    Args:
        cls: Base class to find subclasses for

    Returns:
        List of subclass types
    """
    all_subclasses: list[Type[BaseModel]] = []
    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses


async def init(
    mongo_uri: str,
    database: str,
    **kwargs: Any,
) -> None:
    """Initialize EarnORM with configuration.

    Args:
        mongo_uri: MongoDB connection URI
        database: Database name
        **kwargs: Additional configuration options
    """
    global env, registry, di

    # Initialize container
    await container.init(mongo_uri=mongo_uri, database=database, **kwargs)

    # Update global instances
    di = container
    env = container.registry
    registry = env

    # Get all subclasses of BaseModel
    for model_cls in get_all_subclasses(BaseModel):
        registry.register_model(model_cls)


__all__ = [
    "BaseModel",
    "init",
    # Field types
    "String",
    "Int",
    "Float",
    "Bool",
    "ObjectId",
    "List",
    "Dict",
    # Enhanced char fields
    "Char",
    "Email",
    "Phone",
    "Password",
    # Relation fields
    "Reference",
    "Many2one",
    "One2many",
    "Many2many",
    # DI and Registry
    "di",
    "env",
    "registry",
    "Container",
]
