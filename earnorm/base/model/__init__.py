"""Model package for EarnORM.

This package provides:
- BaseModel: Base class for all models
- MetaModel: Metaclass for model registration
- Model decorators: @multi, @model, @depends

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.base.model.decorators import multi, model, depends
    >>>
    >>> class Partner(BaseModel):
    ...     _name = 'res.partner'
    ...
    ...     @multi
    ...     def write(self, values):
    ...         return self._write(values)
    ...
    ...     @model
    ...     def search(cls, domain):
    ...         return cls.browse(cls._search(domain))
"""

from .base import BaseModel
from .decorators import depends, model, multi
from .meta import MetaModel

__all__ = [
    "BaseModel",
    "MetaModel",
    "multi",
    "model",
    "depends",
]
