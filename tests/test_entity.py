"""Test the Configurable LLM entity module."""

from collections import deque
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.configurable_llm.const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT_CACHING,
    DEFAULT,
    PromptCaching,
)
from custom_components.configurable_llm.entity import (
    CitationDetails,
    ConfigurableLLMDeltaStream,
    ConfigurableLLMBaseEntity,
    ContentDetails,
    _convert_content,
    _format_tool,
)


def test_citation_details_empty() -> None:
    """Test CitationDetails with default values."""
    details = CitationDetails()

    assert details.index == 0
    assert details.length == 0
    assert details.citations == []


def test_content_details_empty() -> None:
    """Test ContentDetails with default values."""
    details = ContentDetails()

    assert details.thinking_signature is None
    assert details.redacted_thinking is None
    assert details.container is None
    assert not details.has_citations()
    assert not details.has_content()


def test_content_details_has_content() -> None:
    """Test ContentDetails has_content method."""
    details = ContentDetails()
    assert not details.has_content()

    details.citation_details = [CitationDetails(length=10)]
    assert details.has_content()


def test_content_details_add_citation_detail() -> None:
    """Test ContentDetails add_citation_detail method."""
    details = ContentDetails()
    details.add_citation_detail()

    assert len(details.citation_details) == 1
    assert details.citation_details[0].index == 0


def test_content_details_delete_empty() -> None:
    """Test ContentDetails delete_empty method."""
    details = ContentDetails()
    details.citation_details = [
        CitationDetails(index=0, length=10, citations=[MagicMock()]),
        CitationDetails(index=10, length=0, citations=[]),
        CitationDetails(index=10, length=5, citations=[MagicMock()]),
    ]

    details.delete_empty()

    assert len(details.citation_details) == 2
    assert all(d.citations for d in details.citation_details)


def test_format_tool() -> None:
    """Test _format_tool function."""
    tool = MagicMock()
    tool.name = "test_tool"
    tool.description = "Test tool description"
    tool.parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"},
        },
        "oneOf": "should_be_removed",
    }

    result = _format_tool(tool, None)

    assert result["name"] == "test_tool"
    assert result["description"] == "Test tool description"
    assert "oneOf" not in result["input_schema"]
    assert result["input_schema"]["type"] == "object"


async def test_convert_content_user_messages(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with user messages."""
    user_content1 = MagicMock(spec=conversation.UserContent)
    user_content1.content = "Hello"
    user_content1.role = "user"
    user_content1.attachments = []
    user_content1.tool_calls = []

    user_content2 = MagicMock(spec=conversation.UserContent)
    user_content2.content = "World"
    user_content2.role = "user"
    user_content2.attachments = []
    user_content2.tool_calls = []

    messages, container_id = _convert_content([user_content1, user_content2])

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "Hello"
    assert messages[0]["content"][1]["text"] == "World"
    assert container_id is None


async def test_convert_content_assistant_message(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with assistant message."""
    assistant_content = MagicMock(spec=conversation.AssistantContent)
    assistant_content.content = "Response"
    assistant_content.role = "assistant"
    assistant_content.tool_calls = []
    assistant_content.native = ContentDetails()

    messages, container_id = _convert_content([assistant_content])

    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == "Response"


async def test_convert_content_with_tool_use(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with tool use."""
    assistant_content = MagicMock(spec=conversation.AssistantContent)
    assistant_content.content = "Thinking..."
    assistant_content.role = "assistant"
    assistant_content.native = ContentDetails()

    tool_call = MagicMock()
    tool_call.id = "tool_123"
    tool_call.tool_name = "test_tool"
    tool_call.tool_args = {"param": "value"}
    tool_call.external = False
    assistant_content.tool_calls = [tool_call]

    messages, container_id = _convert_content([assistant_content])

    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert len(messages[0]["content"]) == 2
    assert messages[0]["content"][0]["type"] == "text"
    assert messages[0]["content"][1]["type"] == "tool_use"


async def test_convert_content_with_system_content_raises_error(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with SystemContent raises error."""
    system_content = MagicMock(spec=conversation.SystemContent)
    system_content.role = "system"

    with pytest.raises(HomeAssistantError) as exc_info:
        _convert_content([system_content])

    assert exc_info.value.translation_key == "unexpected_chat_log_content"


async def test_convert_content_with_tool_result(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with tool result."""
    tool_result = MagicMock(spec=conversation.ToolResultContent)
    tool_result.tool_name = "web_search"
    tool_result.tool_call_id = "call_123"
    tool_result.tool_result = {
        "content": [{"type": "web_search_tool_result", "result": "search results"}]
    }
    tool_result.role = "tool_result"

    messages, container_id = _convert_content([tool_result])

    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"][0]["type"] == "web_search_tool_result"


def test_delta_stream_init() -> None:
    """Test ConfigurableLLMDeltaStream initialization."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    stream = MagicMock()

    delta_stream = ConfigurableLLMDeltaStream(chat_log, stream)

    assert delta_stream._chat_log == chat_log
    assert delta_stream._stream == stream
    assert delta_stream._output_tool is None
    assert len(delta_stream._buffer) == 0


def test_delta_stream_with_output_tool() -> None:
    """Test ConfigurableLLMDeltaStream with output tool."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    stream = MagicMock()

    delta_stream = ConfigurableLLMDeltaStream(chat_log, stream, output_tool="test_tool")

    assert delta_stream._output_tool == "test_tool"


async def test_delta_stream_iteration() -> None:
    """Test ConfigurableLLMDeltaStream async iteration."""
    chat_log = MagicMock(spec=conversation.ChatLog)

    # Mock stream with items in buffer
    stream = MagicMock()
    stream.__aiter__ = MagicMock(return_value=stream)
    stream.__anext__ = AsyncMock(side_effect=[{"content": "Hello"}, StopIteration])

    delta_stream = ConfigurableLLMDeltaStream(chat_log, stream)
    delta_stream._buffer = deque([{"content": "Buffered"}])

    result = await delta_stream.__anext__()

    assert result == {"content": "Buffered"}


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


async def test_convert_content_empty_list(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with empty list."""
    messages, container_id = _convert_content([])

    assert messages == []
    assert container_id is None


async def test_convert_content_consecutive_user_messages(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content combines consecutive user messages."""
    user_content1 = MagicMock(spec=conversation.UserContent)
    user_content1.content = "Hello"
    user_content1.role = "user"
    user_content1.attachments = []
    user_content1.tool_calls = []

    user_content2 = MagicMock(spec=conversation.UserContent)
    user_content2.content = "World"
    user_content2.role = "user"
    user_content2.attachments = []
    user_content2.tool_calls = []

    messages, container_id = _convert_content([user_content1, user_content2])

    # Should be combined into a single message
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


async def test_convert_content_tool_result_with_external_tool(
    hass: HomeAssistant,
) -> None:
    """Test _convert_content with external tool result."""
    tool_result = MagicMock(spec=conversation.ToolResultContent)
    tool_result.tool_name = "web_search"
    tool_result.tool_call_id = "call_123"
    tool_result.tool_result = {
        "content": [{"type": "text", "text": "Search results"}]
    }
    tool_result.role = "tool_result"

    messages, container_id = _convert_content([tool_result])

    assert len(messages) == 1
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"][0]["type"] == "web_search_tool_result"


async def test_citation_details_with_existing_citation() -> None:
    """Test ContentDetails preserves existing index when adding a citation detail."""
    details = ContentDetails()
    details.citation_details = [CitationDetails(index=10, length=5)]
    details.add_citation_detail()

    assert details.citation_details[-1].index == 15  # 10 + 5
