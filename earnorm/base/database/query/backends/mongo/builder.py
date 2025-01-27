"""MongoDB query builder implementation.

This module provides MongoDB query builder implementation.
It supports all MongoDB query operators, aggregation pipeline, and domain expressions.

Examples:
    ```python
    # Basic query
    builder = MongoQueryBuilder("users")
    builder.filter({"age": {"$gt": 18}})
    builder.project({"name": 1, "email": 1})
    builder.sort([("name", 1)])
    query = await builder.build()

    # Domain expression query
    builder = MongoQueryBuilder("users")
    query = builder.from_domain([("age", ">", 18)]).build()
    ```
"""

from typing import Any, List, Literal, Protocol, Tuple, Type, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.types import DatabaseModel, JsonDict, ValueType

from .converter import MongoConverter
from .query import MongoQuery

SortSpec = List[Tuple[str, int]]
ModelT = TypeVar("ModelT", bound=DatabaseModel)

Operation = Literal["insert_one", "update", "delete", None]


class QueryBuilder(Protocol[ModelT]):
    """Query builder protocol."""

    async def build(self) -> MongoQuery[ModelT]:
        """Build query."""
        ...


class MongoQueryBuilder(QueryBuilder[ModelT]):
    """MongoDB query builder implementation.

    This class provides a fluent interface for building MongoDB queries.
    It supports all MongoDB query operators, aggregation pipeline, and domain expressions.

    Examples:
        ```python
        builder = MongoQueryBuilder("users")
        builder.filter({"age": {"$gt": 18}})
        builder.project({"name": 1, "email": 1})
        builder.sort([("name", 1)])
        query = await builder.build()
        ```
    """

    def __init__(
        self, collection: AsyncIOMotorCollection[JsonDict], model_type: Type[ModelT]
    ) -> None:
        """Initialize builder.

        Args:
            collection: MongoDB collection
            model_type: Type of model being queried

        Raises:
            ValueError: If collection is None
        """
        self.collection = collection
        self.model_type = model_type
        self._filter: JsonDict = {}
        self._projection: JsonDict = {}
        self._sort: SortSpec = []
        self._skip: int = 0
        self._limit: int = 0
        self._pipeline: List[JsonDict] = []
        self._allow_disk_use = False
        self._hint: Union[str, List[Tuple[str, int]], None] = None
        self._operation: Operation = None
        self._document: JsonDict = {}
        self._update: JsonDict = {}
        self._options: dict[str, Any] = {}
        self._current_field: str = ""
        self._converter = MongoConverter()

    def where(self, field: str) -> "MongoQueryBuilder[ModelT]":
        """Start building field expression.

        Args:
            field: Field name

        Returns:
            Self for chaining

        Raises:
            ValueError: If field name is empty
        """
        if not field:
            raise ValueError("Field name cannot be empty")
        self._current_field = field
        return self

    def _create_expression(
        self, operator: str, value: Union[ValueType, List[ValueType]]
    ) -> JsonDict:
        """Create domain expression from current field and value.

        Args:
            operator: Comparison operator
            value: Value to compare

        Returns:
            MongoDB query format

        Raises:
            ValueError: If no field is selected
        """
        if not self._current_field:
            raise ValueError("No field selected")
        return {self._current_field: {operator: value}}

    def equals(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field equals value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$eq", value)
        return self

    def not_equals(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field not equals value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$ne", value)
        return self

    def greater_than(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field greater than value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$gt", value)
        return self

    def greater_than_or_equal(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field greater than or equal to value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$gte", value)
        return self

    def less_than(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field less than value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$lt", value)
        return self

    def less_than_or_equal(self, value: ValueType) -> "MongoQueryBuilder[ModelT]":
        """Field less than or equal to value.

        Args:
            value: Value to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$lte", value)
        return self

    def in_list(self, values: List[ValueType]) -> "MongoQueryBuilder[ModelT]":
        """Field value in list.

        Args:
            values: List of values to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$in", values)
        return self

    def not_in_list(self, values: List[ValueType]) -> "MongoQueryBuilder[ModelT]":
        """Field value not in list.

        Args:
            values: List of values to compare

        Returns:
            Self for chaining

        Raises:
            ValueError: If no field is selected
        """
        self._filter = self._create_expression("$nin", values)
        return self

    def and_(self) -> "MongoQueryBuilder[ModelT]":
        """Add AND operator.

        Returns:
            Self for chaining
        """
        if not self._filter:
            return self
        expr = {}
        expr["$and"] = [self._filter]
        self._filter = expr
        return self

    def or_(self) -> "MongoQueryBuilder[ModelT]":
        """Add OR operator.

        Returns:
            Self for chaining
        """
        if not self._filter:
            return self
        expr = {}
        expr["$or"] = [self._filter]
        self._filter = expr
        return self

    def not_(self) -> "MongoQueryBuilder[ModelT]":
        """Add NOT operator.

        Returns:
            Self for chaining
        """
        if not self._filter:
            return self
        expr = {}
        expr["$not"] = self._filter
        self._filter = expr
        return self

    def filter(self, **conditions: Any) -> "MongoQueryBuilder[ModelT]":
        """Add filter conditions.

        Args:
            **conditions: Filter conditions

        Returns:
            Self for chaining
        """
        self._filter = self._filter or {}
        self._filter.update(conditions)
        return self

    def project(self, projection: JsonDict) -> "MongoQueryBuilder[ModelT]":
        """Set field projection.

        Args:
            projection: MongoDB projection

        Returns:
            Self for chaining

        Raises:
            ValueError: If projection is not a dict
        """
        self._projection = projection
        return self

    def sort(self, field: str, ascending: bool = True) -> "MongoQueryBuilder[ModelT]":
        """Add sort specification.

        Args:
            field: Field name to sort by
            ascending: Sort direction (True for ascending, False for descending)

        Returns:
            Self for chaining
        """
        self._sort = [(field, 1 if ascending else -1)]
        return self

    def skip(self, skip: int) -> "MongoQueryBuilder[ModelT]":
        """Set number of documents to skip.

        Args:
            skip: Number of documents to skip

        Returns:
            Self for chaining

        Raises:
            ValueError: If skip is negative
        """
        if skip < 0:
            raise ValueError("Skip must be non-negative")
        self._skip = skip
        return self

    def limit(self, limit: int) -> "MongoQueryBuilder[ModelT]":
        """Set maximum number of documents to return.

        Args:
            limit: Maximum number of documents

        Returns:
            Self for chaining

        Raises:
            ValueError: If limit is negative
        """
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        self._limit = limit
        return self

    def pipeline(self, pipeline: List[JsonDict]) -> "MongoQueryBuilder[ModelT]":
        """Set aggregation pipeline.

        Args:
            pipeline: MongoDB aggregation pipeline

        Returns:
            Self for chaining

        Raises:
            ValueError: If pipeline is invalid
        """
        self._pipeline = pipeline
        return self

    def allow_disk_use(self, allow: bool = True) -> "MongoQueryBuilder[ModelT]":
        """Allow disk use for large queries.

        Args:
            allow: Whether to allow disk use

        Returns:
            Self for chaining
        """
        self._allow_disk_use = allow
        return self

    def hint(
        self, hint: Union[str, List[Tuple[str, int]]]
    ) -> "MongoQueryBuilder[ModelT]":
        """Set index hint.

        Args:
            hint: Index hint (name or specification)

        Returns:
            Self for chaining

        Raises:
            ValueError: If hint is invalid
        """
        if isinstance(hint, list):
            for item in hint:
                if item[1] not in (-1, 1):
                    raise ValueError("Hint direction must be 1 or -1")
        self._hint = hint
        return self

    def insert_one(self, document: JsonDict) -> "MongoQueryBuilder[ModelT]":
        """Set document to insert.

        Args:
            document: Document to insert

        Returns:
            Self for chaining
        """
        self._operation = "insert_one"
        self._document = document
        return self

    def update(self, update: JsonDict) -> "MongoQueryBuilder[ModelT]":
        """Set update operation.

        Args:
            update: Update operation

        Returns:
            Self for chaining
        """
        self._operation = "update"
        self._update = update
        return self

    def delete(self) -> "MongoQueryBuilder[ModelT]":
        """Set delete operation.

        Returns:
            Self for chaining
        """
        self._operation = "delete"
        return self

    def options(self, **kwargs: Any) -> "MongoQueryBuilder[ModelT]":
        """Set additional options.

        Args:
            **kwargs: Query options

        Returns:
            Self for chaining
        """
        self._options.update(kwargs)
        return self

    def from_domain(self, domain: JsonDict) -> "MongoQueryBuilder[ModelT]":
        """Build query from domain expression.

        Args:
            domain: Domain expression

        Returns:
            Self for chaining
        """
        self._filter = self._converter.convert(domain)
        return self

    async def build(self) -> MongoQuery[ModelT]:
        """Build MongoDB query.

        Returns:
            MongoDB query
        """
        return MongoQuery[ModelT](
            collection=self.collection,
            model_type=self.model_type,
            filter=self._filter,
            projection=self._projection,
            sort=self._sort,
            skip=self._skip,
            limit=self._limit,
            pipeline=self._pipeline,
            allow_disk_use=self._allow_disk_use,
            hint=self._hint,
            operation=self._operation,
            document=self._document,
            update=self._update,
            options=self._options,
        )
