"""Domain parser implementation."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

from bson import ObjectId

from earnorm.base.domain.expression import DomainExpression
from earnorm.base.domain.operators import DomainOperator

# Type aliases
Condition = Tuple[str, str, Any]  # (field, operator, value)
DomainItem = Union[DomainOperator, Sequence[Any]]  # Domain list item
MongoQuery = Dict[str, Any]


class DomainParser:
    """Domain parser for converting domain expressions to MongoDB queries.

    This class handles:
    - Converting DomainExpression to MongoDB queries
    - Converting logical operators (AND, OR, NOT)
    - Converting comparison operators to MongoDB format
    - Handling special values (ObjectId, etc.)

    Examples:
        >>> from earnorm.base.domain.builder import DomainBuilder
        >>> builder = DomainBuilder()
        >>> expr = (
        ...     builder
        ...     .field("age").greater_than(18)
        ...     .and_()
        ...     .field("active").equals(True)
        ...     .build()
        ... )
        >>> parser = DomainParser()
        >>> parser.parse(expr)
        {'$and': [{'age': {'$gt': 18}}, {'active': True}]}
    """

    def __init__(self) -> None:
        """Initialize parser with operator mapping."""
        self._operator_map = {
            "=": "$eq",
            "!=": "$ne",
            ">": "$gt",
            ">=": "$gte",
            "<": "$lt",
            "<=": "$lte",
            "in": "$in",
            "not in": "$nin",
            "like": "$regex",
            "not like": "$not",
        }

    def parse(self, expression: DomainExpression) -> MongoQuery:
        """Parse domain expression to MongoDB query.

        Args:
            expression: Domain expression to parse

        Returns:
            MongoDB query dict

        Examples:
            >>> from earnorm.base.domain.builder import DomainBuilder
            >>> builder = DomainBuilder()
            >>> expr = builder.field("age").greater_than(18).build()
            >>> parser = DomainParser()
            >>> parser.parse(expr)
            {'age': {'$gt': 18}}
        """
        domain = expression.to_list()
        if not domain:
            return {}

        return self._parse_domain(domain)

    def _parse_domain(self, domain: List[DomainItem]) -> MongoQuery:
        """Parse domain list to MongoDB query.

        Args:
            domain: Domain list to parse

        Returns:
            MongoDB query dict
        """
        # Handle single condition
        if len(domain) == 1 and not isinstance(domain[0], DomainOperator):
            condition = domain[0]
            if len(condition) == 3:
                return self._parse_condition(cast(Condition, tuple(condition)))
            return {}

        # Handle logical operators
        query: MongoQuery = {}
        current_conditions: List[MongoQuery] = []
        current_operator: Optional[str] = None

        for item in domain:
            if isinstance(item, DomainOperator):
                current_operator = self._parse_operator(item)
            elif len(item) == 3:  # type: ignore
                current_conditions.append(
                    self._parse_condition(cast(Condition, tuple(item)))
                )

        if current_conditions:
            if len(current_conditions) == 1:
                query = current_conditions[0]
            elif current_operator:
                query = {current_operator: current_conditions}
            else:
                # Default to AND if no operator specified
                query = {"$and": current_conditions}

        return query

    def _parse_operator(self, operator: DomainOperator) -> str:
        """Convert domain operator to MongoDB operator.

        Args:
            operator: Domain operator to convert

        Returns:
            MongoDB operator string
        """
        if operator == DomainOperator.AND:
            return "$and"
        elif operator == DomainOperator.OR:
            return "$or"
        else:  # NOT
            return "$not"

    def _parse_condition(self, condition: Condition) -> MongoQuery:
        """Parse single condition to MongoDB query.

        Args:
            condition: (field, operator, value) tuple

        Returns:
            MongoDB condition dict

        Raises:
            ValueError: If operator is invalid
            IndexError: If condition tuple has wrong length

        Examples:
            >>> parser = DomainParser()
            >>> parser._parse_condition(("age", ">", 18))
            {'age': {'$gt': 18}}
        """
        field, operator, value = condition
        value = self._parse_value(value)

        # Handle operators
        if operator in self._operator_map:
            mongo_operator = self._operator_map[operator]
            if operator in ("=", "in"):
                return {field: value}
            elif operator == "like":
                return {field: {mongo_operator: value}}
            elif operator == "not like":
                return {field: {mongo_operator: {self._operator_map["like"]: value}}}
            else:
                return {field: {mongo_operator: value}}

        raise ValueError(f"Invalid operator: {operator}")

    def _parse_value(self, value: Any) -> Any:
        """Parse value to MongoDB format.

        Args:
            value: Value to parse

        Returns:
            Parsed value suitable for MongoDB
        """
        # Handle ObjectId
        if isinstance(value, str) and len(value) == 24:
            try:
                return ObjectId(value)
            except Exception:
                pass

        return value
