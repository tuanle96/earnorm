"""Models module for EarnORM.

This module provides model interfaces and base implementations:
- Model interfaces and protocols
- Model lifecycle management
- Model persistence and validation
"""

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.models.lifecycle import Lifecycle
from earnorm.base.models.persistence import Persistence
from earnorm.base.models.validation import Validator

__all__ = ["ModelInterface", "Lifecycle", "Persistence", "Validator"]
