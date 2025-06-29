"""EarnORM Test Suite.

This package contains all tests for the EarnORM project including:
- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for complete workflows
- Performance and benchmark tests

Test Structure:
- tests/unit/: Unit tests for individual modules and classes
- tests/integration/: Integration tests for component interactions
- tests/e2e/: End-to-end tests for complete user workflows
- tests/conftest.py: Shared test configuration and fixtures

Running Tests:
- All tests: pytest
- Unit tests only: pytest tests/unit/
- Integration tests only: pytest tests/integration/
- With coverage: pytest --cov=earnorm
- Parallel execution: pytest -n auto
"""

__version__ = "0.1.4"
__author__ = "EarnORM Team"
