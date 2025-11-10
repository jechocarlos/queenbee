# QueenBee Test Suite

This directory contains the test suite for the QueenBee agent orchestration system.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest configuration and shared fixtures
├── test_config.py           # Configuration loader tests
├── test_queen_complexity.py # Queen complexity analysis tests
├── test_worker_logic.py     # Worker contribution logic tests
└── test_database.py         # Database models and repository tests
```

## Running Tests

### Install Development Dependencies

First, install the development dependencies including pytest:

```bash
pip install -e ".[dev]"
```

### Run All Tests

```bash
# Using pytest directly
pytest tests/ -v

# Or use the test script
bash scripts/run_tests.sh
```

### Run Specific Test Files

```bash
pytest tests/test_config.py -v
pytest tests/test_queen_complexity.py -v
pytest tests/test_worker_logic.py -v
pytest tests/test_database.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run a specific test class
pytest tests/test_config.py::TestDatabaseConfig -v

# Run a specific test method
pytest tests/test_queen_complexity.py::TestComplexityAnalysis::test_simple_request_single_word -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=queenbee --cov-report=html
# Open htmlcov/index.html in browser to view coverage report
```

## Test Categories

### Unit Tests

Test individual components in isolation with mocked dependencies:

- **test_config.py**: Configuration loading and validation
- **test_queen_complexity.py**: Complexity analysis logic
- **test_worker_logic.py**: Contribution decision logic and formatting
- **test_database.py**: Database models and repositories

### Integration Tests (Future)

Tests that verify multiple components working together:

- End-to-end specialist discussion flow
- Database persistence and retrieval
- Real Ollama integration tests

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_example(mock_config, test_session_id, sample_discussion):
    # Use fixtures in your tests
    assert test_session_id is not None
```

### Mocking External Dependencies

Mock database and LLM calls to keep tests fast and isolated:

```python
from unittest.mock import Mock, patch

@patch('queenbee.agents.queen.ChatRepository')
def test_with_mock(mock_repo):
    # Test logic here
    pass
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage for core logic
- **Critical Paths**: 100% coverage for:
  - Complexity analysis
  - Contribution logic
  - Configuration loading
  - Database operations

## Continuous Integration

Tests should be run automatically on:
- Every commit
- Pull requests
- Before releases

## Troubleshooting

### Import Errors

If you see import errors, ensure the package is installed in development mode:

```bash
pip install -e .
```

### Database Tests Failing

Database tests use mocks by default. For integration tests with real database:

1. Ensure PostgreSQL is running
2. Set test database credentials in `.env`
3. Run migrations for test database

### Pytest Not Found

Install development dependencies:

```bash
pip install pytest pytest-cov pytest-asyncio
```

## Future Enhancements

- [ ] Integration tests with real Ollama
- [ ] Performance benchmarking tests
- [ ] Load testing for concurrent specialists
- [ ] End-to-end CLI tests
- [ ] Snapshot testing for discussion outputs
