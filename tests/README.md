# Job Track Now Backend Tests

This directory contains unit tests for the Job Track Now backend application.

## Running Tests

### Inside Docker Container

To run tests inside the backend container:

```bash
docker exec -it api.jobtracknow.com pytest
```

### Run Specific Test Files

```bash
# Test conversion utilities
docker exec -it api.jobtracknow.com pytest tests/test_conversion.py

# Test convert API endpoints
docker exec -it api.jobtracknow.com pytest tests/test_convert_api.py
```

### Run Tests with Verbose Output

```bash
docker exec -it api.jobtracknow.com pytest -v
```

### Run Tests with Coverage

```bash
docker exec -it api.jobtracknow.com pytest --cov=app --cov-report=html
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_conversion.py` - Tests for the Conversion utility class
- `test_convert_api.py` - Tests for the convert API endpoints

## Test Coverage

The tests cover:

1. **Conversion Utilities**
   - File format conversions (DOCX, ODT, PDF to MD/HTML)
   - Personal settings-based conversion routing
   - Error handling for unsupported formats
   - Subprocess error handling

2. **Convert API Endpoints**
   - `/v1/convert/file` - Smart conversion with personal settings
   - `/v1/convert/final` - Final resume conversion
   - Legacy endpoints (docx2md, docx2html, etc.)
   - Error handling and validation

## Adding New Tests

When adding new conversion methods or endpoints:

1. Add test cases to the appropriate test file
2. Use mocking to avoid external dependencies (databases, file systems)
3. Test both success and error cases
4. Ensure tests are isolated and don't depend on each other
