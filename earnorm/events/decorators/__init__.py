"""Event decorators."""

from .model import after_delete, after_save, before_delete, before_save

__all__ = ["before_save", "after_save", "before_delete", "after_delete"]
