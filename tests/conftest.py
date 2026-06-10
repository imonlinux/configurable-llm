"""Fixtures for Configurable LLM tests."""

import base64
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from anthropic.types import ModelInfo
from homeassistant import setup
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.configurable_llm import (
    ConfigurableLLMConfigEntry,
    ConfigurableLLMCoordinator,
)
from custom_components.configurable_llm.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CODE_EXECUTION,
    CONF_MAX_TOKENS,
    CONF_PROMPT_CACHING,
    CONF_THINKING_BUDGET,
    CONF_THINKING_EFFORT,
    CONF_TOOL_SEARCH,
    CONF_WEB_FETCH,
    CONF_WEB_FETCH_MAX_USES,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_MAX_USES,
    CONF_WEB_SEARCH_USER_LOCATION,
    DEFAULT,
    DOMAIN,
)


@pytest.fixture
def mock_api_key() -> str:
    """Return a mock API key."""
    return "sk-ant-test123456789"


@pytest.fixture
def mock_base_url() -> str:
    """Return a mock base URL."""
    return "https://api.anthropic.com"


@pytest.fixture
def mock_config_data(mock_api_key: str, mock_base_url: str) -> dict:
    """Return mock config entry data."""
    return {
        "api_key": mock_api_key,
        CONF_BASE_URL: mock_base_url,
    }


@pytest.fixture
def mock_options() -> dict:
    """Return mock options."""
    return {
        CONF_CHAT_MODEL: "claude-3-5-sonnet-20241022",
        CONF_MAX_TOKENS: 4096,
        CONF_PROMPT_CACHING: "prompt",
        CONF_THINKING_BUDGET: 1024,
        CONF_THINKING_EFFORT: "medium",
        CONF_CODE_EXECUTION: False,
        CONF_WEB_SEARCH: False,
        CONF_WEB_SEARCH_MAX_USES: 5,
        CONF_WEB_SEARCH_USER_LOCATION: False,
        CONF_WEB_FETCH: False,
        CONF_WEB_FETCH_MAX_USES: 5,
        CONF_TOOL_SEARCH: False,
    }


@pytest.fixture
def mock_models_list() -> list[ModelInfo]:
    """Return mock models list from API."""
    return [
        ModelInfo(
            type="model",
            id="claude-3-5-sonnet-20241022",
            display_name="Claude 3.5 Sonnet",
            created_at=datetime(2024, 10, 22, tzinfo=UTC),
        ),
        ModelInfo(
            type="model",
            id="claude-3-5-haiku-20241022",
            display_name="Claude 3.5 Haiku",
            created_at=datetime(2024, 10, 22, tzinfo=UTC),
        ),
        ModelInfo(
            type="model",
            id="claude-3-opus-20240229",
            display_name="Claude 3 Opus",
            created_at=datetime(2024, 2, 29, tzinfo=UTC),
        ),
    ]


@pytest.fixture
def mock_coordinator(mock_models_list: list[ModelInfo]) -> MagicMock:
    """Return a mock coordinator with model-resolution methods stubbed.

    Entity construction calls coordinator.get_model_info(...) and
    coordinator.get_default_model(...), so both must return realistic values.
    """
    coordinator = MagicMock()
    coordinator.data = mock_models_list
    coordinator.get_model_info = MagicMock(return_value=(mock_models_list[0], True))
    coordinator.get_default_model = MagicMock(return_value=mock_models_list[0].id)
    return coordinator


@pytest.fixture
def mock_anthropic_client(mock_models_list: list[ModelInfo]) -> MagicMock:
    """Return a mock Anthropic client."""
    client = MagicMock(spec=anthropic.AsyncAnthropic)
    client.models.list = AsyncMock(return_value=MagicMock(data=mock_models_list))
    client.messages.create = AsyncMock()
    return client


@pytest.fixture
def mock_config_entry(
    hass: HomeAssistant,
    mock_config_data: dict,
    mock_options: dict,
) -> ConfigEntry:
    """Return a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.title = "Configurable LLM"
    entry.data = mock_config_data
    entry.options = mock_options
    entry.state = "loaded"
    entry.subentries = {}
    entry.runtime_data = None
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value= MagicMock())
    return entry


@pytest.fixture
def mock_subentry_conversation(mock_options: dict) -> ConfigSubentry:
    """Return a mock conversation subentry."""
    subentry = MagicMock(spec=ConfigSubentry)
    subentry.subentry_id = "test_conversation_id"
    subentry.subentry_type = "conversation"
    subentry.title = "Test Conversation"
    subentry.unique_id = "test_conversation_unique_id"
    subentry.data = {
        **mock_options,
        "name": "Test Conversation",
        "prompt": "You are a helpful assistant.",
        "llm_hass_api": None,
    }
    return subentry


@pytest.fixture
def mock_subentry_ai_task(mock_options: dict) -> ConfigSubentry:
    """Return a mock AI task subentry."""
    subentry = MagicMock(spec=ConfigSubentry)
    subentry.subentry_id = "test_ai_task_id"
    subentry.subentry_type = "ai_task_data"
    subentry.title = "Test AI Task"
    subentry.unique_id = "test_ai_task_unique_id"
    subentry.data = {
        **mock_options,
        "name": "Test AI Task",
    }
    return subentry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_anthropic_client: MagicMock,
) -> ConfigurableLLMConfigEntry:
    """Set up the integration for testing."""
    mock_config_entry.runtime_data = ConfigurableLLMCoordinator(
        hass, mock_config_entry
    )
    mock_config_entry.runtime_data.client = mock_anthropic_client
    mock_config_entry.runtime_data.async_set_updated_data(
        mock_anthropic_client.models.list.return_value.data
    )

    await hass.config_entries.async_add(mock_config_entry)
    await hass.async_block_till_done()

    return mock_config_entry


@pytest.fixture
def entity_registry(hass: HomeAssistant) -> er.EntityRegistry:
    """Return the entity registry."""
    return er.async_get(hass)


@pytest.fixture
def mock_add_entities() -> AddEntitiesCallback:
    """Return a mock add entities callback."""
    return AsyncMock()


@pytest.fixture
def mock_file_path(tmp_path) -> str:
    """Create a mock image file for testing attachments."""
    file_path = tmp_path / "test_image.jpg"
    # Create a minimal valid JPEG
    file_path.write_bytes(
        base64.b64decode(
            "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsL"
            "DBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wB"
            "DAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
            "MjIyMjIyMjIyMjIyMjIyMjL/wAARCABIAADASIAAhEBAxEB/8QAFQABAQAAAAA"
            "AAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAA"
            "AAAAAAAAAAAA/9oADAMBAAIRAxEAPwA="
        )
    )
    return str(file_path)


@pytest.fixture
def mock_pdf_path(tmp_path) -> str:
    """Create a mock PDF file for testing attachments."""
    file_path = tmp_path / "test.pdf"
    # Create a minimal valid PDF header
    file_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 0\n/Kids []\n>>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n110\n%%EOF")
    return str(file_path)
