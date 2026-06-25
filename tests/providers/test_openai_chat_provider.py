"""Test the OpenAI Chat Completions provider."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
)
from homeassistant.helpers.update_coordinator import UpdateFailed
import voluptuous as vol

from custom_components.configurable_llm.const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_OPENAI,
)
from custom_components.configurable_llm.providers.base import (
    ProviderError,
    ProviderRequestContext,
)
from custom_components.configurable_llm.providers.openai_chat_provider import (
    OpenAIChatProvider,
    _convert_content,
    _transform_stream,
)

provider = OpenAIChatProvider()


# --------------------------------------------------------------------------- #
# _convert_content
# --------------------------------------------------------------------------- #
async def test_convert_content_user(hass: HomeAssistant) -> None:
    """User content becomes a user message."""
    user = MagicMock(spec=conversation.UserContent)
    user.content = "Hello"
    user.attachments = []

    messages = _convert_content([user])

    assert messages == [{"role": "user", "content": "Hello"}]


async def test_convert_content_assistant_with_tool_calls(
    hass: HomeAssistant,
) -> None:
    """Assistant content carries text + tool_calls."""
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.tool_name = "set_temperature"
    tool_call.tool_args = {"value": 21}

    assistant = MagicMock(spec=conversation.AssistantContent)
    assistant.content = "Doing it"
    assistant.tool_calls = [tool_call]

    messages = _convert_content([assistant])

    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"] == "Doing it"
    assert messages[0]["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "set_temperature", "arguments": '{"value": 21}'},
        }
    ]


async def test_convert_content_tool_result(hass: HomeAssistant) -> None:
    """ToolResultContent becomes a tool message tied to the call id."""
    tool_result = MagicMock(spec=conversation.ToolResultContent)
    tool_result.tool_call_id = "call_1"
    tool_result.tool_result = {"ok": True}

    messages = _convert_content([tool_result])

    assert messages == [
        {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'}
    ]


async def test_convert_content_system_raises(hass: HomeAssistant) -> None:
    """SystemContent is not handled by _convert_content (handled by build_request)."""
    system = MagicMock(spec=conversation.SystemContent)

    with pytest.raises(HomeAssistantError) as exc_info:
        _convert_content([system])

    assert exc_info.value.translation_key == "unexpected_chat_log_content"


# --------------------------------------------------------------------------- #
# _transform_stream
# --------------------------------------------------------------------------- #
async def _aiter(chunks: list[Any]):
    for chunk in chunks:
        yield chunk


def _delta_chunk(
    *,
    role: str | None = None,
    content: str | None = None,
    tool_calls: list[Any] | None = None,
    finish_reason: str | None = None,
) -> Any:
    delta = SimpleNamespace(role=role, content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(usage=None, choices=[choice])


def _usage_chunk(prompt_tokens: int, completion_tokens: int) -> Any:
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    return SimpleNamespace(usage=usage, choices=[])


def _tool_call_delta(
    index: int, id: str | None, name: str | None, arguments: str | None
) -> Any:
    return SimpleNamespace(
        index=index,
        id=id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


async def test_transform_stream_text(hass: HomeAssistant) -> None:
    """Text deltas produce an assistant role then content deltas."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    chunks = [
        _delta_chunk(role="assistant"),
        _delta_chunk(content="Hello"),
        _delta_chunk(content=" world"),
        _delta_chunk(finish_reason="stop"),
        _usage_chunk(5, 2),
    ]

    deltas = [d async for d in _transform_stream(chat_log, _aiter(chunks), output_tool=None)]

    assert {"role": "assistant"} in deltas
    assert {"content": "Hello"} in deltas
    assert {"content": " world"} in deltas
    # usage traced
    chat_log.async_trace.assert_called_once()
    traced = chat_log.async_trace.call_args.args[0]
    assert traced["stats"]["input_tokens"] == 5
    assert traced["stats"]["output_tokens"] == 2


async def test_transform_stream_tool_calls_accumulate_and_flush(
    hass: HomeAssistant,
) -> None:
    """Fragmented tool-call arguments accumulate by index and flush on finish."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    chunks = [
        _delta_chunk(role="assistant"),
        _delta_chunk(
            tool_calls=[_tool_call_delta(0, "call_1", "set_temp", '{"value":')]
        ),
        _delta_chunk(tool_calls=[_tool_call_delta(0, None, None, " 21}")]),
        _delta_chunk(finish_reason="tool_calls"),
    ]

    deltas = [d async for d in _transform_stream(chat_log, _aiter(chunks), output_tool=None)]

    tool_call_deltas = [d for d in deltas if "tool_calls" in d]
    assert len(tool_call_deltas) == 1
    tool_input = tool_call_deltas[0]["tool_calls"][0]
    assert tool_input.id == "call_1"
    assert tool_input.tool_name == "set_temp"
    assert tool_input.tool_args == {"value": 21}


async def test_transform_stream_missing_role(hass: HomeAssistant) -> None:
    """Servers that omit delta.role still get a synthesized assistant role."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    chunks = [
        _delta_chunk(content="Hi"),  # no role
        _delta_chunk(finish_reason="stop"),
    ]

    deltas = [d async for d in _transform_stream(chat_log, _aiter(chunks), output_tool=None)]

    # An assistant role delta must precede the content.
    assert deltas[0] == {"role": "assistant"}
    assert deltas[1] == {"content": "Hi"}


async def test_transform_stream_parallel_tool_calls(hass: HomeAssistant) -> None:
    """Two tool calls on different indices flush together."""
    chat_log = MagicMock(spec=conversation.ChatLog)
    chunks = [
        _delta_chunk(role="assistant"),
        _delta_chunk(
            tool_calls=[
                _tool_call_delta(0, "a", "tool_a", '{"x": 1}'),
                _tool_call_delta(1, "b", "tool_b", '{"y": 2}'),
            ]
        ),
        _delta_chunk(finish_reason="tool_calls"),
    ]

    deltas = [d async for d in _transform_stream(chat_log, _aiter(chunks), output_tool=None)]

    # Each tool call is emitted as its own delta (mirrors the Anthropic stream);
    # HA assembles consecutive tool_calls deltas into one assistant turn.
    tool_call_deltas = [d for d in deltas if "tool_calls" in d]
    assert len(tool_call_deltas) == 2
    names = {
        tc.tool_name for delta in tool_call_deltas for tc in delta["tool_calls"]
    }
    assert names == {"tool_a", "tool_b"}
    # Only a single assistant role delta precedes them.
    assert deltas.count({"role": "assistant"}) == 1


# --------------------------------------------------------------------------- #
# build_request
# --------------------------------------------------------------------------- #
def _ctx(
    *,
    options: dict[str, Any] | None = None,
    structure_name: str | None = None,
    structure: vol.Schema | None = None,
    with_tools: bool = False,
    attachments: list[Any] | None = None,
) -> ProviderRequestContext:
    chat_log = MagicMock(spec=conversation.ChatLog)
    system = MagicMock(spec=conversation.SystemContent)
    system.content = "You are helpful."
    user = MagicMock(spec=conversation.UserContent)
    user.content = "Hi"
    user.role = "user"
    user.attachments = attachments or []
    chat_log.content = [system, user]
    chat_log.llm_api = None
    if with_tools:
        api = MagicMock()
        tool = MagicMock()
        tool.name = "turn_on"
        tool.description = "Turn on"
        tool.parameters = {"type": "object", "properties": {}}
        api.tools = [tool]
        api.custom_serializer = None
        chat_log.llm_api = api
    model = MagicMock()
    model.id = "gpt-4o-mini"
    return ProviderRequestContext(
        hass=None,  # type: ignore[arg-type]
        chat_log=chat_log,
        model=model,
        options=options if options is not None else dict(DEFAULT_OPENAI),
        structure_name=structure_name,
        structure=structure,
    )


async def test_build_request_basic(hass: HomeAssistant) -> None:
    """System is the first message; stream + usage are requested."""
    request, structure_name = await provider.build_request(_ctx())

    assert request["model"] == "gpt-4o-mini"
    assert request["messages"][0] == {"role": "system", "content": "You are helpful."}
    assert request["messages"][1] == {"role": "user", "content": "Hi"}
    assert request["stream"] is True
    assert request["stream_options"] == {"include_usage": True}
    assert structure_name is None


async def test_build_request_sampling_params(hass: HomeAssistant) -> None:
    """temperature/top_p/reasoning_effort are forwarded; 'none' effort omitted."""
    options = {
        CONF_MAX_TOKENS: 512,
        CONF_TEMPERATURE: 0.7,
        CONF_TOP_P: 0.8,
        CONF_REASONING_EFFORT: "high",
    }
    request, _ = await provider.build_request(_ctx(options=options))

    assert request["temperature"] == 0.7
    assert request["top_p"] == 0.8
    assert request["reasoning_effort"] == "high"

    # 'none' effort must not be sent.
    options[CONF_REASONING_EFFORT] = "none"
    request, _ = await provider.build_request(_ctx(options=options))
    assert "reasoning_effort" not in request


async def test_build_request_tools(hass: HomeAssistant) -> None:
    """HA tools become Chat Completions function tools."""
    request, _ = await provider.build_request(_ctx(with_tools=True))

    assert len(request["tools"]) == 1
    tool = request["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "turn_on"
    assert tool["function"]["description"] == "Turn on"


async def test_build_request_structured_output(hass: HomeAssistant) -> None:
    """Structure is emitted as response_format json_schema and consumed."""
    schema = vol.Schema({vol.Required("answer"): str})
    request, structure_name = await provider.build_request(
        _ctx(structure_name="extract", structure=schema)
    )

    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["name"] == "extract"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert structure_name is None  # consumed


async def test_build_request_image_attachments(hass: HomeAssistant) -> None:
    """Image attachments are appended as image_url parts on the user message."""
    attachment = MagicMock()
    attachment.path = "ignored"  # prepare_files is bypassed via patch
    attachment.mime_type = "image/png"
    ctx = _ctx(attachments=[attachment])

    async def fake_prepare_files(_hass, _model, files):
        return [{"type": "image_url", "image_url": {"url": "data:..."}}]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(provider, "prepare_files", fake_prepare_files)
        request, _ = await provider.build_request(ctx)

    user_msg = request["messages"][-1]
    assert isinstance(user_msg["content"], list)
    assert user_msg["content"][0] == {"type": "text", "text": "Hi"}
    assert user_msg["content"][1]["type"] == "image_url"


# --------------------------------------------------------------------------- #
# prepare_files
# --------------------------------------------------------------------------- #
async def test_prepare_files_image(hass: HomeAssistant, tmp_path) -> None:
    """An image becomes an image_url data block."""
    from pathlib import Path

    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)  # content irrelevant

    model = MagicMock()
    model.display_name = "gpt-4o-mini"

    result = await provider.prepare_files(hass, model, [(Path(image_path), None)])

    blocks = list(result)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "image_url"
    assert blocks[0]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_prepare_files_pdf_rejected(hass: HomeAssistant, tmp_path) -> None:
    """PDFs are not supported by Chat Completions and are rejected."""
    from pathlib import Path

    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 not a real pdf")

    model = MagicMock()
    model.display_name = "gpt-4o-mini"

    with pytest.raises(HomeAssistantError) as exc_info:
        await provider.prepare_files(hass, model, [(Path(pdf_path), None)])

    assert exc_info.value.translation_key == "wrong_file_type"


# --------------------------------------------------------------------------- #
# model listing / errors
# --------------------------------------------------------------------------- #
def test_normalize_model() -> None:
    """An OpenAI Model is normalized into a ModelInfo descriptor."""
    raw = SimpleNamespace(id="llama-3-70b", created=1700000000, owned_by="meta")
    info = provider.normalize_model(raw)

    assert info.id == "llama-3-70b"
    assert info.display_name == "llama-3-70b"
    assert info.capabilities is None
    assert info.created_at == datetime.fromtimestamp(1700000000, UTC)


async def test_async_list_models_success(hass: HomeAssistant) -> None:
    """A successful list returns normalized descriptors."""
    client = MagicMock()
    paged = MagicMock()
    paged.data = [
        SimpleNamespace(id="gpt-4o-mini", created=1700000000, owned_by="openai")
    ]
    client.with_options.return_value.models.list = AsyncMock(return_value=paged)

    models = await provider.async_list_models(client)

    assert len(models) == 1
    assert models[0].id == "gpt-4o-mini"


async def test_async_list_models_auth_error(hass: HomeAssistant) -> None:
    """An auth error maps to ConfigEntryAuthFailed."""
    client = MagicMock()
    err = openai.AuthenticationError(
        message="bad key", response=MagicMock(), body=None
    )
    client.with_options.return_value.models.list = AsyncMock(side_effect=err)

    with pytest.raises(ConfigEntryAuthFailed):
        await provider.async_list_models(client)


async def test_async_list_models_generic_error(hass: HomeAssistant) -> None:
    """A generic API error maps to UpdateFailed."""
    client = MagicMock()
    err = openai.BadRequestError(message="nope", response=MagicMock(), body=None)
    client.with_options.return_value.models.list = AsyncMock(side_effect=err)

    with pytest.raises(UpdateFailed):
        await provider.async_list_models(client)


def test_categorize_error() -> None:
    """Provider errors classify into the shared categories."""
    assert provider.categorize_error(
        openai.AuthenticationError(message="x", response=MagicMock(), body=None)
    ) is ProviderError.AUTH
    assert provider.categorize_error(
        openai.APITimeoutError(request=MagicMock())
    ) is ProviderError.TIMEOUT
    assert provider.categorize_error(
        openai.APIConnectionError(request=MagicMock())
    ) is ProviderError.CONNECTION
    assert provider.categorize_error(
        openai.BadRequestError(message="x", response=MagicMock(), body=None)
    ) is ProviderError.OTHER


def test_diagnostics_metadata() -> None:
    """Diagnostics reports the openai SDK version."""
    meta = provider.diagnostics_metadata()
    assert meta == {"client": f"openai=={openai.__version__}"}


def test_defaults() -> None:
    """OpenAI exposes its DEFAULT_OPENAI option dict via the provider interface."""
    assert provider.defaults() == DEFAULT_OPENAI
    assert provider.defaults()[CONF_CHAT_MODEL] == "gpt-4o-mini"
