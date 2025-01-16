"""Domain operators implementation."""

from enum import Enum, auto


class DomainOperator(Enum):
    """Domain operators enum.

    This enum defines the logical operators used in domain expressions:
    - AND: Logical AND operator
    - OR: Logical OR operator
    - NOT: Logical NOT operator

    Examples:
        >>> DomainOperator.AND
        <DomainOperator.AND>
        >>> DomainOperator.OR
        <DomainOperator.OR>
    """

    AND = auto()
    OR = auto()
    NOT = auto()
