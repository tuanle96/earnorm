Queries
=======

The query system in EarnORM provides a powerful and flexible way to retrieve and filter data from MongoDB.

Basic Queries
-----------

Simple Search
~~~~~~~~~~~

.. code-block:: python

    # Basic search with conditions
    users = await User.search([
        ("age", ">=", 18),
        ("status", "=", "active")
    ])

    # Search with OR conditions
    users = await User.search([
        "|",
        ("role", "=", "admin"),
        ("role", "=", "manager")
    ])

    # Complex conditions
    users = await User.search([
        ("age", ">=", 18),
        "&",
        "|",
        ("role", "=", "admin"),
        ("role", "=", "manager"),
        ("is_active", "=", True)
    ])

Operators
~~~~~~~~

Available operators:

- Comparison: `=`, `!=`, `>`, `>=`, `<`, `<=`
- String: `like`, `ilike`, `not like`, `not ilike`
- List: `in`, `not in`
- Null: `is null`, `is not null`
- Logical: `&` (AND), `|` (OR), `!` (NOT)

Examples:

.. code-block:: python

    # String operators
    users = await User.search([
        ("email", "like", "@example.com"),
        ("name", "ilike", "john")
    ])

    # List operators
    products = await Product.search([
        ("category", "in", ["electronics", "computers"]),
        ("status", "not in", ["discontinued", "out_of_stock"])
    ])

    # Null operators
    users = await User.search([
        ("deleted_at", "is null")
    ])

Domain Builder
------------

For complex queries, use the DomainBuilder:

.. code-block:: python

    from earnorm.domain import DomainBuilder

    # Build complex query
    domain = (
        DomainBuilder()
        .field("age").greater_than(18)
        .and_()
        .open_group()
            .field("role").in_(["admin", "manager"])
            .or_()
            .field("status").equals("active")
        .close_group()
        .build()
    )

    users = await User.search(domain)

Available Methods
~~~~~~~~~~~~~~

Comparison Methods:
    - equals(value)
    - not_equals(value)
    - greater_than(value)
    - greater_equals(value)
    - less_than(value)
    - less_equals(value)

String Methods:
    - like(pattern)
    - ilike(pattern)
    - not_like(pattern)
    - not_ilike(pattern)

List Methods:
    - in_(values)
    - not_in(values)

Logical Methods:
    - and_()
    - or_()
    - not_()
    - open_group()
    - close_group()

Sorting and Pagination
-------------------

Sort Options
~~~~~~~~~~

.. code-block:: python

    # Single field sorting
    users = await User.search(
        [("is_active", "=", True)],
        sort=[("name", 1)]  # 1 for ascending, -1 for descending
    )

    # Multiple field sorting
    users = await User.search(
        [("is_active", "=", True)],
        sort=[
            ("role", -1),
            ("name", 1)
        ]
    )

Pagination
~~~~~~~~~

.. code-block:: python

    # Skip and limit
    users = await User.search(
        [("is_active", "=", True)],
        skip=0,
        limit=10
    )

    # With sorting
    users = await User.search(
        [("is_active", "=", True)],
        sort=[("name", 1)],
        skip=10,
        limit=10
    )

Aggregation
---------

Basic Aggregation
~~~~~~~~~~~~~~

.. code-block:: python

    # Simple group by
    result = await User.aggregate([
        {"$match": {"age": {"$gte": 18}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "avg_age": {"$avg": "$age"}
        }}
    ])

Complex Aggregation
~~~~~~~~~~~~~~~~

.. code-block:: python

    # Complex pipeline
    pipeline = [
        {"$match": {"is_active": True}},
        {"$lookup": {
            "from": "orders",
            "localField": "_id",
            "foreignField": "user_id",
            "as": "orders"
        }},
        {"$unwind": "$orders"},
        {"$group": {
            "_id": "$_id",
            "name": {"$first": "$name"},
            "total_orders": {"$sum": 1},
            "total_spent": {"$sum": "$orders.amount"}
        }},
        {"$sort": {"total_spent": -1}},
        {"$limit": 10}
    ]

    top_customers = await User.aggregate(pipeline)

Projection
--------

Field Selection
~~~~~~~~~~~~~

.. code-block:: python

    # Select specific fields
    users = await User.search(
        [("is_active", "=", True)],
        fields=["name", "email"]
    )

    # Exclude fields
    users = await User.search(
        [("is_active", "=", True)],
        exclude=["password", "secret_key"]
    )

Nested Fields
~~~~~~~~~~~

.. code-block:: python

    # Select nested fields
    users = await User.search(
        [("is_active", "=", True)],
        fields=["name", "address.city", "settings.theme"]
    )

Performance
---------

Query Optimization
~~~~~~~~~~~~~~~

1. **Use Indexes**
   - Create indexes for frequently queried fields
   - Use compound indexes for multi-field queries
   - Consider index direction for sorting

2. **Limit Results**
   - Always use pagination for large result sets
   - Select only needed fields
   - Use aggregation for complex calculations

3. **Query Structure**
   - Use appropriate operators
   - Optimize complex conditions
   - Consider query patterns

Monitoring
~~~~~~~~~

.. code-block:: python

    # Enable query logging
    import logging
    logging.getLogger("earnorm.query").setLevel(logging.DEBUG)

    # Use query profiling
    from earnorm.profiler import profile_query

    with profile_query() as profiler:
        users = await User.search([...])
        print(profiler.stats)

Best Practices
------------

1. **Query Design**
   - Keep queries simple and focused
   - Use appropriate operators
   - Consider query reusability
   - Document complex queries

2. **Performance**
   - Create necessary indexes
   - Use projection wisely
   - Monitor slow queries
   - Batch operations when possible

3. **Security**
   - Validate user input
   - Use parameterized queries
   - Implement proper access control
   - Handle sensitive data carefully

4. **Maintenance**
   - Document query patterns
   - Monitor query performance
   - Update indexes regularly
   - Clean up unused queries

Next Steps
---------

- Learn about :doc:`models` structure
- Understand :doc:`fields` types
- Work with :doc:`relationships`
- See :doc:`examples/queries` for more examples
