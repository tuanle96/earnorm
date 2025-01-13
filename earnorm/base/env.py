"""Global environment for EarnORM."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from earnorm.base.registry import Registry

env: "Registry" = None  # type: ignore

__all__ = ["env"]
