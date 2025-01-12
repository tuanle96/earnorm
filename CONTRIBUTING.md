# Contributing to EarnORM

👋 First off, thanks for taking the time to contribute!

## 🚀 Quick Start

1. **Fork and Clone**
```bash
git clone https://github.com/yourusername/earnorm.git
cd earnorm
```

2. **Set Up Development Environment**
```bash
# Using devcontainer (recommended)
code .
# Press F1 -> "Dev Containers: Reopen in Container"

# Or manual setup
poetry install
pre-commit install
```

3. **Create a Branch**
```bash
git checkout -b feature/your-feature-name
```

## 💻 Development Workflow

### Local Development

1. **Run Tests**
```bash
# Run all tests
poetry run pytest

# Run specific test
poetry run pytest tests/test_specific.py

# Run with coverage
poetry run pytest --cov=earnorm
```

2. **Code Quality**
```bash
# Format code
poetry run black .
poetry run isort .

# Check types
poetry run mypy .

# Run linter
poetry run flake8
```

3. **Documentation**
```bash
# Build docs
poetry run mkdocs build

# Serve docs locally
poetry run mkdocs serve
```

### Making Changes

1. Write tests for your changes
2. Implement your changes
3. Update documentation if needed
4. Run the test suite
5. Run code quality checks
6. Commit your changes

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

Example:
```
feat: add async support to User model

- Add async methods for CRUD operations
- Update documentation with async examples
- Add tests for async functionality
```

## 📝 Pull Request Process

1. **Update Documentation**
   - Add/update docstrings for new/modified functions
   - Update README.md if needed
   - Add examples for new features

2. **Run Quality Checks**
   - Ensure all tests pass
   - Fix any linting issues
   - Maintain code coverage

3. **Create Pull Request**
   - Use a clear title following commit conventions
   - Describe your changes in detail
   - Link related issues
   - Add screenshots if relevant

4. **Code Review**
   - Address review comments
   - Keep discussions focused
   - Be patient and respectful

## 🎯 What to Contribute

### Good First Issues
Look for issues labeled with:
- `good first issue`
- `help wanted`
- `documentation`
- `tests`

### Current Focus Areas
1. **Performance Improvements**
   - Query optimization
   - Caching enhancements
   - Connection pooling

2. **Feature Development**
   - Additional field types
   - New decorators
   - CLI improvements

3. **Testing**
   - Unit tests
   - Integration tests
   - Performance benchmarks

4. **Documentation**
   - API documentation
   - Usage examples
   - Best practices

## 📋 Style Guide

### Python Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints
- Maximum line length: 88 characters (Black default)
- Use docstrings for all public APIs

### Documentation Style
- Clear and concise
- Include code examples
- Use proper formatting
- Keep it up to date

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the CC BY-NC License.

## 🤝 Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## 🙋‍♂️ Getting Help

- Create an issue for bugs/features
- Join our [Discord community](https://discord.gg/earnorm)
- Email us at [contact@earnorm.dev](mailto:contact@earnorm.dev)

## 🎉 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Featured on our website

Thank you for contributing to EarnORM! 🚀 