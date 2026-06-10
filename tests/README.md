# Test Suite for Configurable LLM Integration

This test suite provides comprehensive coverage for the Configurable LLM Home Assistant integration.

## Running Tests

### Local Development

1. Install test dependencies:
```bash
pip install -r requirements_test.txt
```

2. Run all tests:
```bash
pytest
```

3. Run specific test file:
```bash
pytest tests/test_coordinator.py
```

4. Run with coverage:
```bash
pytest --cov=custom_components/configurable_llm --cov-report=html
```

5. Run with verbose output:
```bash
pytest -v
```

### Docker Testing

Using the phantom-python-tester container:

```bash
docker run --rm -v $(pwd):/app phantom-python-tester:latest
```

## Test Structure

- `conftest.py` - Shared fixtures for all tests
- `test_init.py` - Tests for main integration setup
- `test_coordinator.py` - Tests for API client and model fetching
- `test_entity.py` - Tests for base entity and LLM interactions
- `test_conversation.py` - Tests for conversation agent entity
- `test_ai_task.py` - Tests for AI task entity
- `test_config_flow.py` - Tests for configuration flow

## Test Coverage Goals

For HACS submission, aim for:
- 80%+ code coverage
- All public APIs tested
- Error paths tested
- Edge cases covered

## CI/CD Integration

These tests can be integrated into GitHub Actions:

```yaml
- name: Run tests
  run: |
    pip install -r requirements_test.txt
    pytest --cov=custom_components/configurable_llm
```
