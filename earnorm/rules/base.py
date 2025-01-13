"""Base interfaces for rule management."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RuleManager(Protocol):
    """Protocol for rule manager."""

    async def check_rules(self, model: Any) -> None:
        """Check rules.

        Args:
            model: Model instance to check rules against
        """
        ...
