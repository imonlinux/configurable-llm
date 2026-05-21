"""Test the Configurable LLM config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from homeassistant.config_entries import ConfigEntry, SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_NAME, CONF_PROMPT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.configurable_llm.config_flow import (
    ConfigurableLLMConfigFlow,
    ConversationSubentryFlowHandler,
    validate_input,
)
from custom_components.configurable_llm.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CODE_EXECUTION,
    CONF_MAX_TOKENS,
    CONF_PROMPT_CACHING,
    CONF_RECOMMENDED,
    CONF_THINKING_BUDGET,
    CONF_WEB_SEARCH,
    DEFAULT,
    DEFAULT_BASE_URL,
)


async def test_validate_input_success(
    hass: HomeAssistant,
    mock_api_key: str,
    mock_anthropic_client: MagicMock,
) -> None:
    """Test validate_input with valid credentials."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        await validate_input(
            hass,
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
        )

        mock_anthropic_client.models.list.assert_called_once_with(timeout=10.0)


async def test_validate_input_timeout(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with timeout."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=anthropic.APITimeoutError(
            message="Request timeout"
        ))
        mock_anthropic.return_value = mock_client

        with pytest.raises(anthropic.APITimeoutError):
            await validate_input(
                hass,
                {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
            )


async def test_validate_input_invalid_url(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with invalid URL format."""
    with pytest.raises(ValueError, match="Base URL must start with"):
        await validate_input(
            hass,
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: "invalid-url"},
        )


async def test_validate_input_auth_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with authentication error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(
            side_effect=anthropic.APIStatusError(
                message="Unauthorized",
                type="authentication_error",
                response=MagicMock(),
                body={"error": {"type": "authentication_error"}},
            )
        )
        mock_anthropic.return_value = mock_client

        with pytest.raises(anthropic.APIStatusError):
            await validate_input(
                hass,
                {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
            )


async def test_flow_step_user(
    hass: HomeAssistant,
    mock_api_key: str,
    mock_anthropic_client: MagicMock,
) -> None:
    """Test user step creates entry."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Configurable LLM"
    assert result["data"][CONF_API_KEY] == mock_api_key
    assert result["data"][CONF_BASE_URL] == DEFAULT_BASE_URL
    assert len(result["subentries"]) == 2


async def test_flow_step_user_show_form(
    hass: HomeAssistant,
) -> None:
    """Test user step shows form."""
    flow = ConfigurableLLMConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "data_schema" in result


async def test_flow_step_user_timeout_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test user step with timeout error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=anthropic.APITimeoutError(
            message="Request timeout"
        ))
        mock_anthropic.return_value = mock_client

        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "timeout_connect"


async def test_flow_step_user_auth_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test user step with authentication error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(
            side_effect=anthropic.APIStatusError(
                message="Unauthorized",
                type="authentication_error",
                response=MagicMock(),
                body={"error": {"type": "authentication_error"}},
            )
        )
        mock_anthropic.return_value = mock_client

        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "authentication_error"


async def test_flow_step_reauth(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reauth step."""
    mock_config_entry.data = {CONF_API_KEY: "old-key"}

    flow = ConfigurableLLMConfigFlow()
    flow.hass = hass
    flow.context = {"entry_id": mock_config_entry.entry_id}

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_get_entry",
        return_value=mock_config_entry,
    ):
        result = await flow.async_step_reauth(mock_config_entry.data)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_flow_subentry_conversation_init(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test conversation subentry init step."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ):
        result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_flow_subentry_conversation_recommended(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test conversation subentry with recommended settings."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ):
        result = await flow.async_step_init({
            CONF_NAME: "Test Conversation",
            CONF_RECOMMENDED: True,
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_flow_subentry_advanced_step(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry advanced step."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.runtime_data.get_default_model = MagicMock(
        return_value=mock_models_list[0].id
    )
    mock_config_entry.runtime_data.get_model_info = MagicMock(
        return_value=(mock_models_list[0], True)
    )

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {CONF_RECOMMENDED: False}

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ):
        result = await flow.async_step_advanced({
            CONF_CHAT_MODEL: mock_models_list[0].id,
            CONF_PROMPT_CACHING: DEFAULT[CONF_PROMPT_CACHING],
        })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "model"


async def test_flow_subentry_model_step(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry model step creates entry."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {
        CONF_NAME: "Test",
        CONF_CHAT_MODEL: mock_models_list[0].id,
        CONF_MAX_TOKENS: DEFAULT[CONF_MAX_TOKENS],
        CONF_CODE_EXECUTION: DEFAULT[CONF_CODE_EXECUTION],
        CONF_WEB_SEARCH: DEFAULT[CONF_WEB_SEARCH],
    }
    flow.model_info = mock_models_list[0]

    result = await flow.async_step_model({})

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_flow_subentry_thinking_budget_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry model step with thinking budget too large."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {CONF_NAME: "Test"}
    flow.model_info = mock_models_list[0]

    result = await flow.async_step_model({
        CONF_MAX_TOKENS: 3000,
        CONF_THINKING_BUDGET: 4000,
        CONF_CODE_EXECUTION: DEFAULT[CONF_CODE_EXECUTION],
        CONF_WEB_SEARCH: DEFAULT[CONF_WEB_SEARCH],
    })

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_THINKING_BUDGET] == "thinking_budget_too_large"


async def test_flow_subentry_entry_not_loaded(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test subentry init with entry not loaded."""
    mock_config_entry.state = ConfigEntryState.NOT_LOADED

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    result = await flow.async_step_init({})

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_loaded"


async def test_flow_get_model_list(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test _get_model_list returns available models."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    models = flow._get_model_list()

    assert len(models) == len(mock_models_list)
    assert models[0]["value"] == mock_models_list[0].id
    assert models[0]["label"] == mock_models_list[0].display_name


async def test_flow_subentry_reconfigure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry reconfiguration."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.subentries = {"test_id": mock_subentry_conversation}

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "reconfigure"
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow._get_reconfigure_subentry = MagicMock(return_value=mock_subentry_conversation)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ):
        result = await flow.async_step_reconfigure(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_flow_subentry_recommended_skips_advanced(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test that recommended settings skip advanced and model steps."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._subentry_type = "conversation"
    flow.source = "user"
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ):
        result = await flow.async_step_init({
            CONF_NAME: "Test",
            CONF_RECOMMENDED: True,
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test"
