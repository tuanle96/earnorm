"""Domain expressions interface.

This module defines interfaces for domain expressions used in queries.
Domain expressions are used to build query conditions in a type-safe way.

Examples:
    >>> # Using domain expressions
    >>> expr = DomainExpression([("age", ">", 18), "&", ("status", "=", "active")])
    >>> expr.validate()  # Validates expression structure
    >>> 
    >>> # Using domain nodes
    >>> root = DomainNode("&", [
    ...     DomainLeaf("age", ">", 18),
    ...     DomainLeaf("status", "=", "active")
    ... ])
    >>> expr = DomainExpression.from_node(root)
"""

from typing import Any, List, Literal, Optional, Tuple, TypeVar, Union

from earnorm.types import JsonDict

T = TypeVar("T")

DomainOperator = Literal[
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
    "is null",
    "is not null",
]

LogicalOperator = Literal["&", "|", "!"]

DomainTuple = Tuple[str, DomainOperator, Any]
DomainItem = Union[DomainTuple, LogicalOperator]


class DomainLeaf:
    """Domain leaf node.

    This class represents a leaf node in the domain expression tree.
    Leaf nodes contain field comparisons like field > value.

    Args:
        field: Field name
        operator: Comparison operator
        value: Value to compare against
    """

    def __init__(self, field: str, operator: DomainOperator, value: Any) -> None:
        """Initialize leaf node.

        Args:
            field: Field name
            operator: Comparison operator
            value: Value to compare against
        """
        self.field = field
        self.operator = operator
        self.value = value

    def validate(self) -> None:
        """Validate leaf node.

        Raises:
            ValueError: If field is empty or operator is invalid
        """
        if not self.field:
            raise ValueError("Field name cannot be empty")
        if self.operator not in DomainOperator.__args__:  # type: ignore
            raise ValueError(f"Invalid operator: {self.operator}")


class DomainNode:
    """Domain logical node.

    This class represents a logical node in the domain expression tree.
    Logical nodes contain AND/OR/NOT operations.

    Args:
        operator: Logical operator
        operands: List of child nodes
    """

    def __init__(
        self,
        operator: LogicalOperator,
        operands: List[Union["DomainNode", DomainLeaf]],
    ) -> None:
        """Initialize logical node.

        Args:
            operator: Logical operator
            operands: List of child nodes
        """
        self.operator = operator
        self.operands = operands

    def validate(self) -> None:
        """Validate logical node.

        Raises:
            ValueError: If operator is invalid or operands are invalid
        """
        if self.operator not in LogicalOperator.__args__:  # type: ignore
            raise ValueError(f"Invalid logical operator: {self.operator}")

        if self.operator == "!" and len(self.operands) != 1:
            raise ValueError("NOT operator requires exactly one operand")

        for operand in self.operands:
            operand.validate()


class DomainExpression:
    """Domain expression.

    This class represents a complete domain expression.
    It contains a tree of domain nodes that can be validated and converted.

    Args:
        domain: Domain expression in list format
    """

    def __init__(self, domain: List[DomainItem]) -> None:
        """Initialize domain expression.

        Args:
            domain: Domain expression in list format
        """
        self.domain = domain
        self.root: Optional[Union[DomainNode, DomainLeaf]] = None
        self._build_tree()

    @classmethod
    def from_node(cls, root: Union[DomainNode, DomainLeaf]) -> "DomainExpression":
        """Create domain expression from root node.

        Args:
            root: Root node of expression tree

        Returns:
            Domain expression
        """
        expr = cls([])
        expr.root = root
        return expr

    def _build_tree(self) -> None:
        """Build expression tree from domain list.

        This method converts the domain list into a tree of nodes.
        The tree can then be validated and converted to a query.
        """
        if not self.domain:
            return

        # Handle single condition
        if len(self.domain) == 3 and isinstance(self.domain[1], str):
            domain_tuple = tuple(self.domain)
            self.root = DomainLeaf(
                str(domain_tuple[0]),
                validate_domain_operator(str(domain_tuple[1])),
                domain_tuple[2],
            )
            return

        # Handle multiple conditions
        stack: List[Union[DomainNode, DomainLeaf]] = []
        operators: List[LogicalOperator] = []

        i = 0
        while i < len(self.domain):
            item = self.domain[i]

            if isinstance(item, (list, tuple)):
                # Leaf node
                domain_tuple = tuple(item)
                if len(domain_tuple) != 3:
                    raise ValueError(f"Invalid condition: {item}")
                leaf = DomainLeaf(
                    str(domain_tuple[0]),
                    validate_domain_operator(str(domain_tuple[1])),
                    domain_tuple[2],
                )
                stack.append(leaf)
                i += 1
            elif item in ("&", "|"):
                # AND/OR operator
                operators.append(validate_logical_operator(str(item)))
                i += 1
            elif item == "!":
                # NOT operator
                if i + 1 >= len(self.domain):
                    raise ValueError("Missing operand for NOT operator")
                next_item = self.domain[i + 1]
                if not isinstance(next_item, (list, tuple)):
                    raise ValueError(f"Invalid NOT operand: {next_item}")
                domain_tuple = tuple(next_item)
                if len(domain_tuple) != 3:
                    raise ValueError(f"Invalid NOT operand: {next_item}")
                leaf = DomainLeaf(
                    str(domain_tuple[0]),
                    validate_domain_operator(str(domain_tuple[1])),
                    domain_tuple[2],
                )
                node = DomainNode("!", [leaf])
                stack.append(node)
                i += 2
            else:
                raise ValueError(f"Invalid domain item: {item}")

        # Build tree from stack and operators
        if not stack:
            return

        if not operators:
            self.root = stack[0]
            return

        # Process operators in order of precedence
        for op in ("&", "|"):
            new_stack: List[Union[DomainNode, DomainLeaf]] = []
            curr_ops: List[LogicalOperator] = []
            operands: List[Union[DomainNode, DomainLeaf]] = []

            for i, item in enumerate(stack):
                if i < len(operators) and operators[i] == op:
                    operands.append(item)
                else:
                    if operands:
                        operands.append(item)
                        node = DomainNode(validate_logical_operator(op), operands)
                        new_stack.append(node)
                        operands = []
                    else:
                        new_stack.append(item)

                if i < len(operators):
                    curr_ops.append(operators[i])

            stack = new_stack
            operators = curr_ops

        self.root = stack[0]

    def validate(self) -> None:
        """Validate domain expression.

        Raises:
            ValueError: If expression is invalid
        """
        if self.root is None:
            return
        self.root.validate()

    def to_list(self) -> List[Any]:
        """Convert domain expression to list format.

        Returns:
            Domain expression in list format
        """
        return self.domain

    def to_dict(self) -> JsonDict:
        """Convert domain expression to dict format.

        Returns:
            Domain expression in dict format
        """
        result: JsonDict = {}
        for item in self.domain:
            if isinstance(item, (list, tuple)):
                field, _, value = item
                result[field] = value
        return result


def validate_domain_operator(op: str) -> DomainOperator:
    """Validate and convert string to DomainOperator.

    Args:
        op: Operator string to validate

    Returns:
        Valid DomainOperator

    Raises:
        ValueError: If operator is invalid
    """
    if op not in DomainOperator.__args__:  # type: ignore
        raise ValueError(f"Invalid domain operator: {op}")
    return op  # type: ignore


def validate_logical_operator(op: str) -> LogicalOperator:
    """Validate and convert string to LogicalOperator.

    Args:
        op: Operator string to validate

    Returns:
        Valid LogicalOperator

    Raises:
        ValueError: If operator is invalid
    """
    if op not in LogicalOperator.__args__:  # type: ignore
        raise ValueError(f"Invalid logical operator: {op}")
    return op  # type: ignore
