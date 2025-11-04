# Testing Guide

Quick reference for running tests in the Identity API Backend.

## The Import Error You Saw

```
ModuleNotFoundError: No module named 'src'
```

This happens when running pytest locally without the correct Python path. **Solution: Run tests in Docker or set PYTHONPATH.**

## ✅ Recommended: Run Tests in Docker

The easiest and most reliable way:

```bash
# Start services first
./scripts/start.sh

# Run all tests
docker compose exec api pytest

# Run with coverage
docker compose exec api pytest --cov=src --cov-report=term-missing

# Run with HTML coverage report
docker compose exec api pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Running Specific Tests

```bash
# Unit tests only (fast)
docker compose exec api pytest tests/unit/ -v

# Integration tests only
docker compose exec api pytest tests/integration/ -v

# Specific test file
docker compose exec api pytest tests/unit/test_models.py -v

# Specific test function
docker compose exec api pytest tests/unit/test_models.py::test_create_base_profile -v

# Tests matching a pattern
docker compose exec api pytest -k "profile" -v

# Stop on first failure
docker compose exec api pytest -x

# Show print statements
docker compose exec api pytest -s
```

## Alternative: Run Tests Locally

If you want to run tests outside Docker (e.g., in your IDE):

### One-time setup:

```bash
# Install dependencies
cd /Users/lucacipriani/Devs/thesis/backend
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH=/Users/lucacipriani/Devs/thesis/backend:$PYTHONPATH
```

### Add to your shell profile (~/.zshrc):

```bash
# Add this line to make it permanent
export PYTHONPATH="/Users/lucacipriani/Devs/thesis/backend:$PYTHONPATH"
```

### Then run tests:

```bash
cd /Users/lucacipriani/Devs/thesis/backend
pytest --cov=src
```

## Test Coverage Goals

- **Minimum:** 80% code coverage
- **Unit tests:** Test individual components with mocked dependencies
- **Integration tests:** Test API endpoints with real database

## Current Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_config.py      # Configuration tests
│   ├── test_models.py      # Model tests
│   └── test_database.py    # Database module tests
└── integration/
    ├── test_endpoints.py           # API endpoint tests
    └── test_database_integration.py # Database operation tests
```

## Common Test Commands

```bash
# Quick test run
docker compose exec api pytest

# Full coverage report
docker compose exec api pytest --cov=src --cov-report=term-missing --cov-report=html

# Verbose output
docker compose exec api pytest -vv

# Only failed tests from last run
docker compose exec api pytest --lf

# Run tests and stop on first failure
docker compose exec api pytest -x

# Run tests in parallel (faster)
docker compose exec api pytest -n auto
```

## Debugging Tests

```bash
# Run with print statements visible
docker compose exec api pytest -s

# Run with Python debugger
docker compose exec api pytest --pdb

# Very verbose output
docker compose exec api pytest -vv --tb=long
```

## IDE Configuration

### VS Code (settings.json)

```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.envFile": "${workspaceFolder}/backend/.env",
  "python.testing.pytestArgs": [
    "tests",
    "--cov=src"
  ],
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}/backend"
  }
}
```

### PyCharm

1. Go to **Run** → **Edit Configurations**
2. Add **pytest** configuration
3. Set **Working directory** to `/Users/lucacipriani/Devs/thesis/backend`
4. Add environment variable: `PYTHONPATH=/Users/lucacipriani/Devs/thesis/backend`

## Continuous Testing

Watch for file changes and rerun tests:

```bash
# Install pytest-watch
docker compose exec api pip install pytest-watch

# Run in watch mode
docker compose exec api ptw
```

## Quick Troubleshooting

### Tests fail with database errors
```bash
./scripts/reset.sh  # Reset database
docker compose exec api pytest
```

### Import errors in tests
```bash
# Make sure you're running in Docker
docker compose exec api pytest

# Or set PYTHONPATH if running locally
export PYTHONPATH=/Users/lucacipriani/Devs/thesis/backend:$PYTHONPATH
```

### Stale Python cache
```bash
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
```

## Test Fixtures Available

From `tests/conftest.py`:

- `db_engine` - Test database engine
- `db_session` - Database session
- `client` - FastAPI test client
- `sample_verified_profile` - Sample verified profile
- `sample_unverified_profile` - Sample unverified profile
- `sample_pseudonymous_profile` - Sample pseudonymous profile
- `sample_identity_name` - Sample identity name
- `sample_multilingual_name` - Multilingual name example
- `sample_deprecated_name` - Deprecated name example
- `sample_profiles_with_names` - Multiple profiles with names

## Example Test Session

```bash
# 1. Start services
./scripts/start.sh

# 2. Run all tests
docker compose exec api pytest -v

# 3. Check coverage
docker compose exec api pytest --cov=src --cov-report=term-missing

# 4. Generate HTML report
docker compose exec api pytest --cov=src --cov-report=html

# 5. View report
open htmlcov/index.html

# 6. When done
./scripts/stop.sh
```

That's it! Tests are designed to be easy to run and maintain. 🚀

