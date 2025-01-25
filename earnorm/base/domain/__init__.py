"""Domain module for query building.

This module provides domain expressions and builders for building complex queries.

Examples:
    >>> from earnorm.base.domain import DomainBuilder
    >>> builder = DomainBuilder()
    >>> domain = (
    ...     builder
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
"""

from earnorm.base.domain.builder import DomainBuilder, DomainFieldBuilder
from earnorm.base.domain.expression import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
    DomainVisitor,
    LogicalOp,
    Operator,
)
from earnorm.base.domain.operators import (
    ContainsOperator,
    CustomOperator,
    EndsWithOperator,
    RangeOperator,
    StartsWithOperator,
)

__all__ = [
    # Builder
    "DomainBuilder",
    "DomainFieldBuilder",
    # Expression
    "DomainExpression",
    "DomainLeaf",
    "DomainNode",
    "DomainVisitor",
    "LogicalOp",
    "Operator",
    # Operators
    "CustomOperator",
    "ContainsOperator",
    "EndsWithOperator",
    "RangeOperator",
    "StartsWithOperator",
]
