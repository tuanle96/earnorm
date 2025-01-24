"""Domain expression validator.

This module provides validation for domain expressions.

Examples:
    >>> validator = DomainValidator()
    >>> validator.validate([
    ...     ["age", ">", 18],
    ...     "AND",
    ...     ["status", "=", "active"]
    ... ])
"""

from typing import Any, List, Optional, Set, Union

from earnorm.base.domain.expression import DomainLeaf, DomainNode, LogicalOperator
from earnorm.types import DomainOperator

DomainItem = Union[List[Any], str]
NodeType = Union[DomainNode, DomainLeaf]


class DomainValidationError(Exception):
    """Domain validation error."""

    pass


class DomainValidator:
    """Validator for domain expressions.

    Examples:
        >>> validator = DomainValidator()
        >>> validator.validate([
        ...     ["age", ">", 18],
        ...     "AND",
        ...     ["status", "=", "active"]
        ... ])
    """

    # Define valid operators
    VALID_OPERATORS: Set[DomainOperator] = {
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
        "in",
        "not in",
        "like",
        "ilike",
        "not like",
        "not ilike",
        "=like",
        "=ilike",
        "contains",
        "not contains",
    }

    def validate(self, domain: List[DomainItem]) -> None:
        """Validate domain expression.

        Args:
            domain: Domain expression to validate

        Raises:
            DomainValidationError: If domain is invalid

        Examples:
            >>> validator.validate([
            ...     ["age", ">", 18],
            ...     "AND",
            ...     ["status", "=", "active"]
            ... ])
        """
        if not domain:
            return

        # Validate structure
        self._validate_structure(domain)

        # Parse and validate tree
        tree = self._parse(domain)
        if tree:
            self._validate_tree(tree)

    def _validate_structure(self, domain: List[DomainItem]) -> None:
        """Validate domain list structure.

        Args:
            domain: Domain expression list

        Raises:
            DomainValidationError: If structure is invalid
        """
        for i, item in enumerate(domain):
            # Validate leaf
            if isinstance(item, list):
                if len(item) != 3:
                    raise DomainValidationError(
                        f"Invalid leaf at position {i}: must have 3 elements"
                    )
                if not isinstance(item[0], str):
                    raise DomainValidationError(
                        f"Invalid field at position {i}: must be string"
                    )
                if not isinstance(item[1], str):
                    raise DomainValidationError(
                        f"Invalid operator at position {i}: must be string"
                    )
                operator = item[1]
                if operator not in self.VALID_OPERATORS:
                    raise DomainValidationError(
                        f"Invalid operator at position {i}: {operator}"
                    )

            # Validate operator
            elif isinstance(item, str):  # type: ignore
                try:
                    LogicalOperator(item)
                except ValueError:
                    raise DomainValidationError(
                        f"Invalid logical operator at position {i}: {item}"
                    )

            else:
                raise DomainValidationError(
                    f"Invalid item at position {i}: must be list or string"
                )

    def _parse(self, domain: List[DomainItem], pos: int = 0) -> Optional[NodeType]:
        """Parse domain expression list into tree.

        Args:
            domain: Domain expression list
            pos: Current position in list

        Returns:
            Root node of expression tree
        """
        if not domain:
            return None

        # Parse first expression
        if isinstance(domain[pos], list):
            operator = domain[pos][1]
            if not isinstance(operator, str):
                raise ValueError(f"Invalid operator type: {type(operator)}")
            if operator not in self.VALID_OPERATORS:
                raise ValueError(f"Invalid operator: {operator}")
            left = DomainLeaf(
                field=domain[pos][0],
                operator=operator,  # Type is checked above
                value=domain[pos][2],
            )
        else:
            left = self._parse(domain, pos + 1)

        # Check if we're done
        if pos + 1 >= len(domain):
            return left

        # Parse operator
        if not isinstance(domain[pos + 1], str):
            return left

        op = LogicalOperator(domain[pos + 1])

        # Parse right side
        if pos + 2 >= len(domain):
            raise ValueError("Missing right operand")

        if isinstance(domain[pos + 2], list):
            operator = domain[pos + 2][1]
            if not isinstance(operator, str):
                raise ValueError(f"Invalid operator type: {type(operator)}")
            if operator not in self.VALID_OPERATORS:
                raise ValueError(f"Invalid operator: {operator}")
            right = DomainLeaf(
                field=domain[pos + 2][0],
                operator=operator,  # Type is checked above
                value=domain[pos + 2][2],
            )
        else:
            right = self._parse(domain, pos + 3)

        # Create node with type-safe children
        children = [left] if left else []
        if right:
            children.append(right)

        return DomainNode(op, children)

    def _validate_tree(self, node: NodeType) -> None:
        """Validate expression tree.

        Args:
            node: Root node to validate

        Raises:
            DomainValidationError: If tree is invalid
        """
        if isinstance(node, DomainLeaf):
            if node.operator not in self.VALID_OPERATORS:
                raise DomainValidationError(f"Invalid operator: {node.operator}")

            # Validate value type for operators
            if node.operator in ("in", "not in"):
                if not isinstance(node.value, (list, tuple)):
                    raise DomainValidationError(
                        f"Value for {node.operator} must be list or tuple"
                    )

            elif node.operator in (
                "like",
                "ilike",
                "not like",
                "not ilike",
                "=like",
                "=ilike",
                "contains",
                "not contains",
            ) and not isinstance(node.value, str):
                raise DomainValidationError(f"Value for {node.operator} must be string")

        else:
            # Validate children
            if not node.children:
                raise DomainValidationError("Node must have children")

            for child in node.children:
                self._validate_tree(child)
