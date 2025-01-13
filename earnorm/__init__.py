"""EarnORM - Async MongoDB ORM."""

import os
from typing import Any, Optional, Union

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

# Global container instance
container = DIContainer()

# Expose commonly used instances
di = container  # DI container alias
env = container.get("registry")  # Odoo-style env alias
registry = env  # Registry alias


async def init(
    config_path: Optional[Union[str, os.PathLike[str]]] = None,
    mongo_uri: Optional[str] = None,
    database: Optional[str] = "earnbase",
    **kwargs: Any,
) -> None:
    """Initialize EarnORM with configuration.

    This function initializes all components of EarnORM including:
    - Dependency Injection container
    - Database connection
    - Model registry
    - Security managers (if configured)

    Args:
        config_path: Path to configuration file (YAML/JSON)
        mongo_uri: MongoDB connection URI (overrides config file)
        database: Database name (overrides config file)
        **kwargs: Additional configuration options
            - security_manager: Custom security manager class
            - lifecycle_manager: Custom lifecycle manager class
            - auto_discover_models: Whether to auto discover models (default: True)
            - model_paths: List of paths to search for models
    """
    # Initialize container
    await container.init(
        config_path=config_path, mongo_uri=mongo_uri, database=database, **kwargs
    )

    # Update global instances
    global env, registry
    env = container.get("registry")
    registry = env


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
