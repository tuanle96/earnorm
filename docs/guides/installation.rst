Installation
============

This guide will help you install EarnORM and its dependencies.

Requirements
-----------

- Python 3.10 or higher
- MongoDB 4.4 or higher
- Poetry (recommended) or pip

Using Poetry (Recommended)
-------------------------

The recommended way to install EarnORM is using Poetry:

.. code-block:: bash

    # Install Poetry if you haven't already
    curl -sSL https://install.python-poetry.org | python3 -

    # Create a new project
    poetry new my-project
    cd my-project

    # Add EarnORM as a dependency
    poetry add earnorm

    # Install all dependencies
    poetry install

Using pip
---------

You can also install EarnORM using pip:

.. code-block:: bash

    pip install earnorm

Optional Dependencies
-------------------

EarnORM has several optional dependencies for additional features:

.. code-block:: bash

    # Install with Redis support (for caching)
    poetry add earnorm[redis]

    # Install with all optional dependencies
    poetry add earnorm[all]

Development Installation
----------------------

If you want to contribute to EarnORM or run tests:

.. code-block:: bash

    # Clone the repository
    git clone https://github.com/earnbase/earnorm.git
    cd earnorm

    # Install dependencies including development tools
    poetry install --with dev,test

    # Run tests
    poetry run pytest

Verifying Installation
--------------------

You can verify your installation by running Python and importing EarnORM:

.. code-block:: python

    import earnorm
    print(earnorm.__version__)

Configuration
------------

After installation, you'll need to configure your MongoDB connection. Create a file named `.env` in your project root:

.. code-block:: bash

    MONGODB_URI=mongodb://localhost:27017
    MONGODB_DB=mydb

Then in your code:

.. code-block:: python

    from earnorm import init

    await init(
        mongo_uri="mongodb://localhost:27017",
        database="mydb"
    )

Next Steps
---------

- Read the :doc:`quickstart` guide to begin using EarnORM
- Check out the :doc:`concepts` to understand EarnORM's core concepts
- See :doc:`examples/basic` for basic usage examples
