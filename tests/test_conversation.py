"""Test the Configurable LLM conversation entity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.configurable_llm.conversation import (
    ConfigurableLLMConversationEntity,
    async_setup_entry,
)


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_add_entities: AddEntitiesCallback,
    mock_coordinator: MagicMock,
) -> None:
    """Test async_setup_entry."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_config_entry.subentries = {
        "test_conversation_id": mock_subentry_conversation,
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    call_args = mock_add_entities.call_args
    assert len(call_args[0][0]) == 1  # One entity added
    assert isinstance(call_args[0][0][0], ConfigurableLLMConversationEntity)
    assert call_args[1]["config_subentry_id"] == "test_conversation_id"


async def test_async_setup_entry_skips_non_conversation(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_add_entities: AddEntitiesCallback,
    mock_coordinator: MagicMock,
) -> None:
    """Test async_setup_entry skips non-conversation subentries."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_ai_task.subentry_type = "ai_task_data"
    mock_config_entry.subentries = {
        "test_ai_task_id": mock_subentry_ai_task,
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should not add any entities since subentry type is ai_task_data
    call_args = mock_add_entities.call_args
    assert call_args is None or len(call_args[0][0]) == 0


async def test_conversation_entity_properties(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test ConfigurableLLMConversationEntity properties."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    assert entity.entity_id == "test_conversation_id"
    assert entity.unique_id == "test_conversation_id"
    assert entity.supports_streaming is True
    assert entity.translation_key == "conversation"
    assert entity.supported_languages == "*"


async def test_conversation_entity_with_hass_api_control(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test ConfigurableLLMConversationEntity with HA API control enabled."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_conversation.data["llm_hass_api"] = "assist"

    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    assert conversation.ConversationEntityFeature.CONTROL in entity.supported_features


async def test_conversation_entity_without_hass_api_control(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test ConfigurableLLMConversationEntity without HA API control."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_conversation.data["llm_hass_api"] = None

    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    assert not hasattr(entity, "supported_features") or (
        conversation.ConversationEntityFeature.CONTROL not in entity.supported_features
    )


async def test_async_handle_message_success(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_handle_message success path."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    user_input = MagicMock(spec=conversation.ConversationInput)
    user_input.text = "Hello"
    user_input.as_llm_context = MagicMock(return_value={})
    user_input.extra_system_prompt = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.async_provide_llm_data = AsyncMock()

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        result = await entity._async_handle_message(user_input, chat_log)

    chat_log.async_provide_llm_data.assert_called_once()
    # Verify _async_handle_chat_log was called
    entity._async_handle_chat_log.assert_called_once_with(chat_log)


async def test_async_handle_message_converse_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_handle_message with ConverseError."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    user_input = MagicMock(spec=conversation.ConversationInput)
    user_input.text = "Hello"
    user_input.as_llm_context = MagicMock(return_value={})
    user_input.extra_system_prompt = None

    chat_log = MagicMock(spec=conversation.ChatLog)

    # Mock async_provide_llm_data to raise ConverseError
    error = conversation.ConverseError("Test error")
    error.as_conversation_result = MagicMock(return_value=MagicMock())
    chat_log.async_provide_llm_data = AsyncMock(side_effect=error)

    result = await entity._async_handle_message(user_input, chat_log)

    # Should return error result from ConverseError
    error.as_conversation_result.assert_called_once()


async def test_async_handle_message_hass_api_uses_options(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_handle_message uses llm_hass_api from options."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_conversation.data["llm_hass_api"] = "assist"

    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    user_input = MagicMock(spec=conversation.ConversationInput)
    user_input.text = "Hello"
    user_input.as_llm_context = MagicMock(return_value={})
    user_input.extra_system_prompt = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.async_provide_llm_data = AsyncMock()

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        await entity._async_handle_message(user_input, chat_log)

    chat_log.async_provide_llm_data.assert_called_once_with(
        {},
        "assist",
        mock_subentry_conversation.data["prompt"],
        None,
    )


async def test_async_handle_message_uses_prompt_from_options(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_handle_message uses prompt from subentry data."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_conversation.data["prompt"] = "You are a helpful assistant."

    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    user_input = MagicMock(spec=conversation.ConversationInput)
    user_input.text = "Hello"
    user_input.as_llm_context = MagicMock(return_value={})
    user_input.extra_system_prompt = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.async_provide_llm_data = AsyncMock()

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        await entity._async_handle_message(user_input, chat_log)

    chat_log.async_provide_llm_data.assert_called_once()
    call_args = chat_log.async_provide_llm_data.call_args.args
    assert call_args[2] == "You are a helpful assistant."  # 3rd positional = prompt


async def test_async_handle_message_with_extra_system_prompt(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_handle_message includes extra system prompt."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMConversationEntity(
        mock_config_entry, mock_subentry_conversation
    )

    user_input = MagicMock(spec=conversation.ConversationInput)
    user_input.text = "Hello"
    user_input.as_llm_context = MagicMock(return_value={})
    user_input.extra_system_prompt = "Additional instruction"

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.async_provide_llm_data = AsyncMock()

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        await entity._async_handle_message(user_input, chat_log)

    chat_log.async_provide_llm_data.assert_called_once()
    call_args = chat_log.async_provide_llm_data.call_args.args
    assert call_args[3] == "Additional instruction"  # 4th positional = extra_system_prompt
