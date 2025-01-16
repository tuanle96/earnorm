"""Query parser implementation."""

from typing import Any, List, Sequence, cast

from bson import ObjectId

from earnorm.base.query.builder import QueryBuilder
from earnorm.base.types import FilterDict, ProjectionDict, QueryParams, SortItem


class QueryParser:
    """MongoDB query parser and validator.

    This class handles:
    - Parsing and validating query components
    - Converting query parameters to MongoDB format
    - Normalizing query values

    Examples:
        >>> parser = QueryParser()
        >>> query = parser.parse({
        ...     "filter": {"age": 18},
        ...     "sort": [("created_at", -1)],
        ...     "limit": 10,
        ...     "offset": 0
        ... })
    """

    def parse(self, params: QueryParams) -> QueryBuilder:
        """Parse query parameters to QueryBuilder.

        Args:
            params: Query parameters dict with components:
                - filter: Dict of filter conditions
                - sort: List of (field, direction) tuples
                - limit: Number of items to return
                - offset: Number of items to skip
                - projection: Fields to include/exclude

        Returns:
            Configured query builder

        Raises:
            ValueError: If any parameter is invalid:
                - filter is not a dict
                - sort is not a list of (field, direction) tuples
                - limit/offset is not a positive integer
                - projection is not a dict

        Examples:
            >>> params = {
            ...     "filter": {"age": 18},
            ...     "sort": [("created_at", -1)],
            ...     "limit": 10,
            ...     "offset": 0
            ... }
            >>> query = parser.parse(params)
        """
        builder = QueryBuilder()

        # Parse filter
        filter_query = params.get("filter", {})
        if not isinstance(filter_query, dict):
            raise ValueError("Filter must be a dict")
        filter_query = cast(FilterDict, filter_query)

        for key, value in filter_query.items():
            if key == "_id" and isinstance(value, str):
                value = ObjectId(value)
            builder.filter(**{str(key): value})

        # Parse sort
        sort_list = params.get("sort", [])
        if not isinstance(sort_list, list):
            raise ValueError("Sort must be a list")
        sort_list = cast(List[Sequence[Any]], sort_list)

        for item in sort_list:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("Sort items must be (field, direction) tuples")
            field, direction = cast(SortItem, item)

            # Type validation
            try:
                str(field)  # Validate field is string-like
            except (TypeError, ValueError):
                raise ValueError("Sort field must be a string")

            try:
                direction_int = int(direction)
                if direction_int not in (-1, 1):
                    raise ValueError
            except (TypeError, ValueError):
                raise ValueError("Sort direction must be 1 or -1")

            builder.sort(str(field), direction_int)

        # Parse limit/offset
        limit = params.get("limit")
        if limit is not None and (not isinstance(limit, int) or limit < 0):
            raise ValueError("Limit must be a positive integer")
        if limit is not None:
            builder.limit(limit)

        offset = params.get("offset")
        if offset is not None and (not isinstance(offset, int) or offset < 0):
            raise ValueError("Offset must be a positive integer")
        if offset is not None:
            builder.offset(offset)

        # Parse projection
        projection = params.get("projection")
        if projection is not None:
            if not isinstance(projection, dict):
                raise ValueError("Projection must be a dict")
            projection = cast(ProjectionDict, projection)
            builder.project(**projection)

        return builder
