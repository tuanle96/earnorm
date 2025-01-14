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
from earnorm.pool.core.connection import Connection

# Global variables
env = None
registry = None
di = None
pool = None

# Global container instance
container = DIContainer()


def get_all_subclasses(cls: Type[models.BaseModel]) -> list[Type[models.BaseModel]]:
    """Get all subclasses of a class recursively."""
    all_subclasses: list[Type[models.BaseModel]] = []
    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))
    return all_subclasses


async def init(
    mongo_uri: str,
    database: str,
    *,
    min_pool_size: int = 5,
    max_pool_size: int = 20,
    pool_timeout: float = 30.0,
    pool_max_lifetime: int = 3600,
    pool_idle_timeout: int = 300,
    **kwargs: Any,
) -> None:
    """Initialize EarnORM with configuration.

    Args:
        mongo_uri: MongoDB connection URI
        database: Database name
        min_pool_size: Minimum connection pool size
        max_pool_size: Maximum connection pool size
        pool_timeout: Connection acquire timeout
        pool_max_lifetime: Maximum connection lifetime
        pool_idle_timeout: Maximum idle time
        **kwargs: Additional configuration options
    """
    global env, registry, di, pool

    # Initialize container with pool configuration
    await container.init(
        mongo_uri=mongo_uri,
        database=database,
        min_pool_size=min_pool_size,
        max_pool_size=max_pool_size,
        pool_timeout=pool_timeout,
        pool_max_lifetime=pool_max_lifetime,
        pool_idle_timeout=pool_idle_timeout,
        **kwargs,
    )

    # Update global instances
    di = container
    env = container.registry
    registry = env
    pool = container.pool

    # Get all subclasses of BaseModel
    for model_cls in get_all_subclasses(models.BaseModel):
        registry.register_model(model_cls)


async def get_connection() -> Connection:
    """Get connection from pool.

    Returns:
        Connection instance
    """
    if pool is None:
        raise RuntimeError("EarnORM not initialized")
    return await pool.acquire()


async def release_connection(conn: Connection) -> None:
    """Release connection back to pool.

    Args:
        conn: Connection to release
    """
    if pool is None:
        raise RuntimeError("EarnORM not initialized")
    await pool.release(conn)


__all__ = [
    "models",
    "init",
    "fields",
    "get_connection",
    "release_connection",
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
