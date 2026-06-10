"""Test the Configurable LLM AI task entity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.configurable_llm.ai_task import (
    ConfigurableLLMTaskEntity,
    async_setup_entry,
)


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_add_entities: AddEntitiesCallback,
    mock_coordinator: MagicMock,
) -> None:
    """Test async_setup_entry."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_config_entry.subentries = {
        "test_ai_task_id": mock_subentry_ai_task,
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    call_args = mock_add_entities.call_args
    assert len(call_args[0][0]) == 1
    assert isinstance(call_args[0][0][0], ConfigurableLLMTaskEntity)
    assert call_args[1]["config_subentry_id"] == "test_ai_task_id"


async def test_async_setup_entry_skips_non_ai_task(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_add_entities: AddEntitiesCallback,
    mock_coordinator: MagicMock,
) -> None:
    """Test async_setup_entry skips non-AI task subentries."""
    mock_config_entry.runtime_data = mock_coordinator
    mock_subentry_conversation.subentry_type = "conversation"
    mock_config_entry.subentries = {
        "test_conversation_id": mock_subentry_conversation,
    }

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should not add any entities since subentry type is conversation
    call_args = mock_add_entities.call_args
    assert call_args is None or len(call_args[0][0]) == 0


async def test_ai_task_entity_properties(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test ConfigurableLLMTaskEntity properties."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    assert entity.unique_id == "test_ai_task_id"
    assert entity.translation_key == "ai_task_data"

    # Check supported features
    assert ai_task.AITaskEntityFeature.GENERATE_DATA in entity.supported_features
    assert ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS in entity.supported_features


async def test_async_generate_data_success_without_structure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_generate_data without structure returns raw text."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    task = MagicMock(spec=ai_task.GenDataTask)
    task.name = "test_task"
    task.structure = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test_conv_id"
    chat_log.content = [
        MagicMock(spec=conversation.SystemContent),
        MagicMock(spec=conversation.UserContent),
        MagicMock(spec=conversation.AssistantContent),
    ]
    chat_log.content[-1].content = "Generated text response"
    chat_log.content[-1].native = None

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        result = await entity._async_generate_data(task, chat_log)

    assert result.conversation_id == "test_conv_id"
    assert result.data == "Generated text response"


async def test_async_generate_data_success_with_structure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_generate_data with structure parses JSON."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    task = MagicMock(spec=ai_task.GenDataTask)
    task.name = "test_task"
    task.structure = MagicMock()

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test_conv_id"
    chat_log.content = [
        MagicMock(spec=conversation.SystemContent),
        MagicMock(spec=conversation.UserContent),
        MagicMock(spec=conversation.AssistantContent),
    ]
    chat_log.content[-1].content = '{"key": "value", "number": 42}'
    chat_log.content[-1].native = None

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        result = await entity._async_generate_data(task, chat_log)

    assert result.conversation_id == "test_conv_id"
    assert result.data == {"key": "value", "number": 42}


async def test_async_generate_data_json_parse_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_generate_data with invalid JSON raises error."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    task = MagicMock(spec=ai_task.GenDataTask)
    task.name = "test_task"
    task.structure = MagicMock()

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test_conv_id"
    chat_log.content = [
        MagicMock(spec=conversation.SystemContent),
        MagicMock(spec=conversation.UserContent),
        MagicMock(spec=conversation.AssistantContent),
    ]
    chat_log.content[-1].content = "This is not valid JSON"
    chat_log.content[-1].native = None

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        with pytest.raises(HomeAssistantError) as exc_info:
            await entity._async_generate_data(task, chat_log)

    assert exc_info.value.translation_key == "json_parse_error"


async def test_async_generate_data_no_assistant_response(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_generate_data when no assistant response exists."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    task = MagicMock(spec=ai_task.GenDataTask)
    task.name = "test_task"
    task.structure = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test_conv_id"
    chat_log.content = [
        MagicMock(spec=conversation.SystemContent),
        MagicMock(spec=conversation.UserContent),
    ]

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()):
        with pytest.raises(HomeAssistantError) as exc_info:
            await entity._async_generate_data(task, chat_log)

    assert exc_info.value.translation_key == "response_not_found"


async def test_async_generate_data_passes_max_iterations(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_ai_task: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Test _async_generate_data passes max_iterations to _async_handle_chat_log."""
    mock_config_entry.runtime_data = mock_coordinator
    entity = ConfigurableLLMTaskEntity(
        mock_config_entry, mock_subentry_ai_task
    )

    task = MagicMock(spec=ai_task.GenDataTask)
    task.name = "test_task"
    task.structure = None

    chat_log = MagicMock(spec=conversation.ChatLog)
    chat_log.conversation_id = "test_conv_id"
    chat_log.content = [
        MagicMock(spec=conversation.SystemContent),
        MagicMock(spec=conversation.UserContent),
        MagicMock(spec=conversation.AssistantContent),
    ]
    chat_log.content[-1].content = "Response"
    chat_log.content[-1].native = None

    with patch.object(entity, "_async_handle_chat_log", new=AsyncMock()) as mock_handle:
        await entity._async_generate_data(task, chat_log)

        mock_handle.assert_called_once()
        call_args = mock_handle.call_args
        assert call_args[0][1] == "test_task"  # task.name
        assert call_args[0][2] is None  # structure (task.structure)
        assert call_args[1]["max_iterations"] == 1000
