"""Test the Configurable LLM entity module."""

from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.configurable_llm.const import PromptCaching
from custom_components.configurable_llm.entity import ConfigurableLLMBaseEntity


async def _empty_aiter():
    """An async generator that yields nothing (stands in for a delta stream)."""
    if False:  # pragma: no cover - makes this an async generator
        yield


async def test_base_entity_init(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_subentry_conversation: ConfigSubentry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test ConfigurableLLMBaseEntity initialization."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.get_model_info = MagicMock(
        return_value=(mock_models_list[0], True)
    )

    entity = ConfigurableLLMBaseEntity(mock_config_entry, mock_subentry_conversation)

    assert entity.entry == mock_config_entry
    assert entity.subentry == mock_subentry_conversation
    assert entity.unique_id == "test_conversation_id"
    assert entity.has_entity_name is True


async def test_base_entity_device_info(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_subentry_conversation: ConfigSubentry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test ConfigurableLLMBaseEntity device info."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.get_model_info = MagicMock(
        return_value=(mock_models_list[0], True)
    )

    entity = ConfigurableLLMBaseEntity(mock_config_entry, mock_subentry_conversation)

    device_info = entity.device_info

    assert device_info["identifiers"] == {("configurable_llm", "test_conversation_id")}
    assert device_info["name"] == "Test Conversation"
    assert device_info["manufacturer"] == "Configurable LLM"
    assert device_info["model"] == "Claude 3.5 Sonnet"


def test_prompt_caching_enum() -> None:
    """Test PromptCaching enum values."""
    assert PromptCaching.OFF.value == "off"
    assert PromptCaching.PROMPT.value == "prompt"
    assert PromptCaching.AUTOMATIC.value == "automatic"


async def test_handle_chat_log_dispatches_to_provider(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_subentry_conversation: ConfigSubentry,
) -> None:
    """The chat loop delegates build/create/transform/convert to the provider."""
    coordinator = MagicMock()
    coordinator.get_model_info = MagicMock(
        return_value=(MagicMock(id="m", display_name="m"), True)
    )
    provider = MagicMock()
    provider.build_request = AsyncMock(return_value=({"messages": []}, None))
    provider.create_stream = AsyncMock(return_value=MagicMock())
    provider.make_transformer.return_value = _empty_aiter()
    provider.convert_back.return_value = ([], None)
    provider.merge_iteration_state.return_value = {"messages": []}
    coordinator.provider = provider

    mock_config_entry.runtime_data = coordinator
    entity = ConfigurableLLMBaseEntity(mock_config_entry, mock_subentry_conversation)
    entity.hass = hass
    entity.entity_id = "conversation.test"

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.content = [MagicMock()]
    chat_log.async_add_delta_content_stream = MagicMock(return_value=_empty_aiter())
    chat_log.unresponded_tool_results = []

    await entity._async_handle_chat_log(chat_log)

    provider.build_request.assert_called_once()
    provider.create_stream.assert_called_once()
    provider.make_transformer.assert_called_once()
    provider.convert_back.assert_called_once()
    coordinator.async_set_updated_data.assert_called_once()


async def test_handle_chat_log_maps_provider_auth_error(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_subentry_conversation: ConfigSubentry,
) -> None:
    """A provider auth error triggers a coordinator refresh + reauth error."""
    from custom_components.configurable_llm.providers.base import ProviderError

    coordinator = MagicMock()
    coordinator.get_model_info = MagicMock(
        return_value=(MagicMock(id="m", display_name="m"), True)
    )
    provider = MagicMock()
    provider.build_request = AsyncMock(return_value=({"messages": []}, None))
    provider.create_stream = AsyncMock(side_effect=ValueError("nope"))
    provider.categorize_error.return_value = ProviderError.AUTH
    coordinator.async_request_refresh = AsyncMock()
    coordinator.provider = provider

    mock_config_entry.runtime_data = coordinator
    entity = ConfigurableLLMBaseEntity(mock_config_entry, mock_subentry_conversation)
    entity.hass = hass
    entity.entity_id = "conversation.test"

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.content = [MagicMock()]
    chat_log.unresponded_tool_results = []

    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError) as exc_info:
        await entity._async_handle_chat_log(chat_log)

    assert exc_info.value.translation_key == "api_authentication_error"
    coordinator.async_request_refresh.assert_awaited_once()
