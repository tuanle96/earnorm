Welcome to EarnORM's documentation!
================================

EarnORM is a high-performance, async-first MongoDB ORM for Python, designed to maximize throughput in I/O-bound applications. Built on top of Motor and Pydantic, it leverages the full power of async/await to handle thousands of database operations concurrently while maintaining type safety and data validation.

Key Features
-----------

- **Async-First Architecture**: Built from ground up with async/await for maximum I/O performance
- **Type Safety & Validation**: Full type hints and runtime validation powered by Pydantic
- **Powerful Query System**: Flexible domain expressions and advanced filtering capabilities
- **Relationship Management**: Comprehensive support for one-to-one, one-to-many, and many-to-many relationships
- **Developer Experience**: Rich set of tools, clear documentation, and extensive examples

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   guides/installation
   guides/quickstart
   guides/concepts

.. toctree::
   :maxdepth: 2
   :caption: Core Documentation

   guides/models
   guides/fields
   guides/queries
   guides/relationships

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   guides/performance
   guides/connections
   guides/best-practices

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/models
   api/fields
   api/queries
   api/relationships

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic
   examples/relationships
   examples/queries

.. toctree::
   :maxdepth: 2
   :caption: Development

   guides/contributing
   guides/changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
