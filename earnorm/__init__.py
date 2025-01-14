"""EarnORM - Async MongoDB ORM."""

from typing import Any, Type

from earnorm import fields
from earnorm.base import model as models
from earnorm.di import Container, DIContainer
from earnorm.fields.base import BooleanField as Bool
from earnorm.fields.base import DictField as Dict
from earnorm.fields.base import FloatField as Float
from earnorm.fields.base import IntegerField as Int
from earnorm.fields.base import ListField as List
from earnorm.fields.base import ObjectIdField as ObjectId
from earnorm.fields.string import EmailStringField as Email
from earnorm.fields.string import PasswordStringField as Password
from earnorm.fields.string import PhoneStringField as Phone
from earnorm.fields.string import StringField as String

# Global variables
env = None
registry = None
di = None

# Global container instance
container = DIContainer()


def get_all_subclasses(cls: Type[models.BaseModel]) -> list[Type[models.BaseModel]]:
    """Get all subclasses of a class recursively.

    Args:
        cls: Base class to find subclasses for

    Returns:
        List of subclass types
    """
    all_subclasses: list[Type[models.BaseModel]] = []
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
    for model_cls in get_all_subclasses(models.BaseModel):
        registry.register_model(model_cls)


__all__ = [
    "models",
    "init",
    "fields",
    # Field Types
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
    # DI and Registry
    "di",
    "env",
    "registry",
    "Container",
]
