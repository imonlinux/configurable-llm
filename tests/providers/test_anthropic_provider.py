"""Test the Anthropic provider (request/stream/content helpers).

These tests were relocated verbatim from ``tests/test_entity.py`` and
``tests/test_coordinator.py`` when the Anthropic logic moved behind the
:class:`LLMProvider` interface; behavior is unchanged.
"""

from collections import deque
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import anthropic
from anthropic.types import ModelInfo
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.configurable_llm.providers.anthropic_provider import (
    AnthropicProvider,
    CitationDetails,
    ConfigurableLLMDeltaStream,
    ContentDetails,
    _convert_content,
    _format_tool,
)

provider = AnthropicProvider()


# --------------------------------------------------------------------------- #
# model_alias (moved from test_coordinator.py)
# --------------------------------------------------------------------------- #
def test_model_alias_anthropic_models() -> None:
    """Test model_alias function with Anthropic models."""
    assert provider.model_alias("claude-3-5-sonnet-20241022") == "claude-3-5-sonnet"
    assert provider.model_alias("claude-3-opus-20240229-1") == "claude-3-opus-20240229-1"
    assert provider.model_alias("claude-3-opus-20240229") == "claude-3-opus"
    assert (
        provider.model_alias("claude-3-5-sonnet-20241022-preview")
        == "claude-3-5-sonnet-20241022-preview"
    )


def test_model_alias_non_anthropic_models() -> None:
    """Test model_alias function with non-Anthropic models."""
    assert provider.model_alias("glm-5.1") == "glm-5.1"
    assert provider.model_alias("z-ai-custom-model") == "z-ai-custom-model"
    assert provider.model_alias("llama-3-70b") == "llama-3-70b"
    assert provider.model_alias("mistral-7b") == "mistral-7b"


def test_model_alias_preserves_non_standard_formatting() -> None:
    """Test that non-Anthropic model IDs are preserved exactly."""
    custom_models = [
        "gpt-4",
        "deepseek-chat",
        "qwen-72b-chat",
        "phi-3-medium-128k-instruct",
    ]
    for model_id in custom_models:
        assert provider.model_alias(model_id) == model_id


def test_defaults() -> None:
    """Anthropic exposes its DEFAULT option dict via the provider interface."""
    from custom_components.configurable_llm.const import DEFAULT

    assert provider.defaults() == DEFAULT


# --------------------------------------------------------------------------- #
# dataclasses (moved from test_entity.py)
# --------------------------------------------------------------------------- #
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


def test_citation_details_with_existing_citation() -> None:
    """Test ContentDetails preserves existing index when adding a citation detail."""
    details = ContentDetails()
    details.citation_details = [CitationDetails(index=10, length=5)]
    details.add_citation_detail()

    assert details.citation_details[-1].index == 15  # 10 + 5


# --------------------------------------------------------------------------- #
# _format_tool (moved from test_entity.py)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# _convert_content (moved from test_entity.py)
# --------------------------------------------------------------------------- #
async def test_convert_content_empty_list(hass: HomeAssistant) -> None:
    """Test _convert_content with empty list."""
    messages, container_id = _convert_content([])

    assert messages == []
    assert container_id is None


async def test_convert_content_user_messages(hass: HomeAssistant) -> None:
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


async def test_convert_content_assistant_message(hass: HomeAssistant) -> None:
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


async def test_convert_content_with_tool_use(hass: HomeAssistant) -> None:
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

    try:
        _convert_content([system_content])
    except HomeAssistantError as err:
        assert err.translation_key == "unexpected_chat_log_content"
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected HomeAssistantError")


async def test_convert_content_with_tool_result(hass: HomeAssistant) -> None:
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


# --------------------------------------------------------------------------- #
# ConfigurableLLMDeltaStream (moved from test_entity.py)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# fetch_model (issue #4: junk models.retrieve results must not block setup)
# --------------------------------------------------------------------------- #
async def test_fetch_model_degrades_on_non_model_result(hass: HomeAssistant) -> None:
    """A raw-str retrieve result (z.ai's empty 200) degrades to safe defaults."""
    coordinator = MagicMock()
    coordinator.client.models.retrieve = AsyncMock(return_value="glm-4.7-flash")

    info, err_key, err_msg = await provider.fetch_model(coordinator, "glm-4.7-flash")

    assert err_key is None
    assert err_msg is None
    assert isinstance(info, ModelInfo)
    assert info.id == "glm-4.7-flash"
    assert info.display_name == "glm-4.7-flash"
    assert info.capabilities is None
    assert info.max_tokens is None


async def test_fetch_model_passthrough_on_real_result(hass: HomeAssistant) -> None:
    """A genuine ModelInfo from retrieve is returned untouched."""
    real = ModelInfo(
        type="model",
        id="glm-4.7",
        created_at=datetime(2025, 12, 22, tzinfo=UTC),
        display_name="GLM-4.7",
        capabilities=None,
        max_tokens=None,
    )
    coordinator = MagicMock()
    coordinator.client.models.retrieve = AsyncMock(return_value=real)

    info, err_key, _ = await provider.fetch_model(coordinator, "glm-4.7")

    assert info is real
    assert err_key is None


async def test_fetch_model_not_found_error(hass: HomeAssistant) -> None:
    """NotFoundError maps to the model_not_found error key."""
    coordinator = MagicMock()
    coordinator.client.models.retrieve = AsyncMock(
        side_effect=anthropic.NotFoundError(
            message="m", response=MagicMock(), body=None
        )
    )

    info, err_key, _ = await provider.fetch_model(coordinator, "does-not-exist")

    assert info is None
    assert err_key == "model_not_found"
