"""Dependency injection module for EarnORM."""

from earnorm.di.container import Container, DIContainer
from earnorm.di.lifecycle import LifecycleHooks, LifecycleManager

# Global instances
container = DIContainer()
lifecycle = container.get_lifecycle()

__all__ = [
    "Container",
    "DIContainer",
    "LifecycleHooks",
    "LifecycleManager",
    "container",
    "lifecycle",
]
