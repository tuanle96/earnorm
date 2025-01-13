"""Domain expressions for EarnORM."""

from typing import Any, Dict, List, Optional, Tuple, Union

# Type definitions
DomainTerm = Tuple[str, str, Any]  # (field, operator, value)
DomainOperator = str  # '&', '|', '!'
DomainElement = Union[DomainTerm, DomainOperator]
Domain = List[DomainElement]

TERM_OPERATORS = {
    "=": "$eq",
    "!=": "$ne",
    ">": "$gt",
    ">=": "$gte",
    "<": "$lt",
    "<=": "$lte",
    "in": "$in",
    "not in": "$nin",
    "like": "$regex",
    "ilike": "$regex",
}


class DomainParser:
    """Parser for domain expressions."""

    def __init__(self, domain: Optional[Domain] = None) -> None:
        """Initialize domain parser.

        Args:
            domain: List of domain expressions
        """
        self.domain = domain or []

    def _parse_term(self, term: DomainTerm) -> Dict[str, Any]:
        """Parse a single domain term.

        Args:
            term: Domain term (field, operator, value)

        Returns:
            MongoDB query dict for the term
        """
        field, op, value = term

        if op not in TERM_OPERATORS:
            raise ValueError(f"Unsupported operator: {op}")

        mongo_op = TERM_OPERATORS[op]

        if op == "like":
            value = str(value).replace("%", ".*")
            return {field: {mongo_op: value}}
        elif op == "ilike":
            value = str(value).replace("%", ".*")
            return {field: {mongo_op: value, "$options": "i"}}
        elif op == "=":
            return {field: value}
        else:
            return {field: {mongo_op: value}}

    def to_mongo_query(self) -> Dict[str, Any]:
        """Convert domain to MongoDB query.

        Returns:
            MongoDB query dict
        """
        if not self.domain:
            return {}

        stack: List[Tuple[str, Dict[str, Any]]] = []
        current: Dict[str, Any] = {}

        for element in self.domain:
            if isinstance(element, tuple):
                # Process term
                term_query = self._parse_term(element)
                if not current:
                    current = term_query
                else:
                    # Implicit AND
                    current = {"$and": [current, term_query]}
            else:
                # Process operator
                if element == "|":
                    # Push current to stack and start new OR group
                    if current:
                        stack.append(("OR", current))
                        current = {}
                elif element == "&":
                    # Push current to stack and start new AND group
                    if current:
                        stack.append(("AND", current))
                        current = {}
                elif element == "!":
                    # Negate the next term
                    if current:
                        stack.append(("NOT", current))
                        current = {}

        # Process remaining stack
        while stack:
            op, prev = stack.pop()
            if op == "OR":
                current = {"$or": [prev, current]}
            elif op == "AND":
                current = {"$and": [prev, current]}
            elif op == "NOT":
                current = {"$not": prev}

        return current
