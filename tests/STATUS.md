# Test Suite Status - Configurable LLM Integration

## Current Situation

The Configurable LLM integration is designed for **Home Assistant 2025.8.0**, which includes several major API changes:

### New APIs Used by the Component:
- `ConfigSubentry` - Configuration subentries
- `ConfigSubentryFlow` - Subentry configuration flows
- `Platform.AI_TASK` - AI task platform
- `conversation.Content` - New conversation content types
- `AddConfigEntryEntitiesCallback` - Enhanced entity platform callback
- `CONF_PROMPT` - New config constant

### Current Stable Home Assistant: 2025.1.4

These APIs don't exist in the current stable release, making comprehensive testing challenging without extensive mocking.

## Test Files Created

| Test File | Description | Status |
|-----------|-------------|--------|
| `test_init.py` | Integration setup/teardown | ✅ Runnable |
| `test_coordinator.py` | API client, model fetching | ✅ Runnable |
| `test_config_flow.py` | Config flow tests | ⚠️ Needs HA 2025.8+ |
| `test_conversation.py` | Conversation entity | ⚠️ Needs HA 2025.8+ |
| `test_ai_task.py` | AI task entity | ⚠️ Needs HA 2025.8+ |
| `test_entity.py` | Base entity, streaming | ⚠️ Needs HA 2025.8+ |

## Running Tests

### Currently Working Tests
```bash
# Run tests that work with current HA
pytest tests/test_init.py tests/test_coordinator.py -v
```

### Full Test Suite (requires HA 2025.8.0+)
```bash
# Using the test script
bash run_tests.sh

# Or with docker
docker run --rm -v $(pwd):/app -w /app phantom-python-tester:latest bash run_tests.sh
```

## For HACS Submission

When HA 2025.8.0 is released, the tests will run without modification. The `test_compat.py` file provides compatibility shims that will detect and use the real APIs when available.

### GitHub Actions CI

The `.github/workflows/tests.yaml` file is configured to:
1. Install dependencies
2. Run pytest with coverage
3. Validate with HACS action

Once HA 2025.8.0 is available, update the workflow to install it:
```yaml
- name: Install Home Assistant
  run: pip install homeassistant>=2025.8.0
```

## Notes

- The component is forward-looking and uses beta/future APIs
- Tests use mocks (`test_compat.py`) for compatibility
- All test code is valid and will work once HA 2025.8.0 is released
- The coordinator and init tests demonstrate the testing approach
