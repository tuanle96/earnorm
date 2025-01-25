"""Model package for EarnORM.

This package provides:
- StoredModel: Base class for persistent models
- AbstractModel: Base class for service/business logic models
- Model decorators: @multi, @model, @depends

Examples:
    >>> from earnorm.base.model import StoredModel, AbstractModel
    >>> from earnorm.base.model.decorators import multi, model, depends
    >>>
    >>> class User(StoredModel):
    ...     _name = 'data.user'
    ...     name = StringField()
    ...
    >>> class UserService(AbstractModel):
    ...     _name = 'service.user'
    ...     async def authenticate(self, user_id: int):
    ...         pass
"""

from .base import BaseModel

__all__ = [
    "BaseModel",
]
