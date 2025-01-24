"""Domain module for query building.

This module provides domain expressions and builders for building complex queries.

Examples:
    >>> from earnorm.base.domain import DomainBuilder, MongoConverter
    >>> builder = DomainBuilder()
    >>> domain = (
    ...     builder
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... )
    >>> converter = MongoConverter()
    >>> mongo_query = converter.convert(domain)
    >>> {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
"""

from earnorm.base.domain.builder import DomainBuilder, DomainFieldBuilder
from earnorm.base.domain.converter import (
    DomainConverter,
    MongoConverter,
    PostgresConverter,
)
from earnorm.base.domain.expression import (
    DomainExpression,
    DomainLeaf,
    DomainNode,
    LogicalOperator,
)

__all__ = [
    # Builder
    "DomainBuilder",
    "DomainFieldBuilder",
    # Expression
    "DomainExpression",
    "DomainLeaf",
    "DomainNode",
    "LogicalOperator",
    # Converter
    "DomainConverter",
    "MongoConverter",
    "PostgresConverter",
]
