"""OpenAI Chat Completions provider for Configurable LLM.

Targets ``/v1/chat/completions`` — the de-facto interoperability standard for
opensource/local LLM inference servers (vLLM, llama.cpp, Ollama, LM Studio,
OpenRouter, Groq, Together, Mistral-compat, ...) and OpenAI itself. This is
*not* OpenAI's Responses API (cloud-only; core's ``openai_conversation`` covers
that). One rail covers most "OpenAI-compatible" endpoints.

OpenAI-compatible ``/v1/models`` endpoints return no capability information, so
this provider ignores capabilities entirely and drives behavior from the
configured options (temperature/top_p/reasoning_effort, tools, structured
output, image attachments).
"""
from __future__ import annotations

import base64
from collections.abc import AsyncIterator, Callable, Iterable
from datetime import UTC, datetime
import json
from mimetypes import guess_file_type
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import openai
from anthropic.types import ModelInfo
import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
)
from homeassistant.helpers import llm
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import slugify

from ..const import (
    CONF_MAX_TOKENS,
    CONF_REASONING_EFFORT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_OPENAI,
    DOMAIN,
    LOGGER,
)
from .base import LLMProvider, ProviderError, ProviderRequestContext

if TYPE_CHECKING:
    from ..coordinator import ConfigurableLLMCoordinator


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> dict[str, Any]:
    """Format a tool as an OpenAI Chat Completions function tool."""
    unsupported_keys = {"oneOf", "anyOf", "allOf", "enum", "not"}
    schema = convert(tool.parameters, custom_serializer=custom_serializer)
    if unsupported_keys.intersection(schema):
        schema = {k: v for k, v in schema.items() if k not in unsupported_keys}

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "parameters": schema,
            "description": tool.description or "",
        },
    }


def _adjust_schema(schema: dict[str, Any]) -> None:
    """Adjust an output schema for OpenAI strict structured output."""
    if schema.get("type") == "object":
        schema.setdefault("strict", True)
        schema.setdefault("additionalProperties", False)
        if "properties" not in schema:
            return

        schema.setdefault("required", [])

        # Ensure all properties are required (strict mode requires this).
        for prop, prop_info in schema["properties"].items():
            _adjust_schema(prop_info)
            if prop not in schema["required"]:
                prop_info["type"] = [prop_info["type"], "null"]
                schema["required"].append(prop)

    elif schema.get("type") == "array":
        if "items" not in schema:
            return
        _adjust_schema(schema["items"])


def _format_structured_output(
    schema: vol.Schema, llm_api: llm.APIInstance | None
) -> dict[str, Any]:
    """Format a schema for OpenAI ``response_format`` json_schema."""
    result: dict[str, Any] = convert(
        schema,
        custom_serializer=(
            llm_api.custom_serializer if llm_api else llm.selector_serializer
        ),
    )
    _adjust_schema(result)
    return result


def _convert_content(
    chat_content: Iterable[conversation.Content],
) -> list[dict[str, Any]]:
    """Transform HA chat_log content into OpenAI Chat Completions messages.

    SystemContent is excluded here; :meth:`OpenAIChatProvider.build_request`
    prepends it as the first message (Chat Completions carries the system
    message inside ``messages``, unlike the Anthropic top-level ``system``).
    """
    messages: list[dict[str, Any]] = []

    for content in chat_content:
        if isinstance(content, conversation.ToolResultContent):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": content.tool_call_id,
                    "content": json.dumps(content.tool_result),
                }
            )
        elif isinstance(content, conversation.UserContent):
            messages.append({"role": "user", "content": content.content})
        elif isinstance(content, conversation.AssistantContent):
            message: dict[str, Any] = {
                "role": "assistant",
                "content": content.content or None,
            }
            if content.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.tool_name,
                            "arguments": json.dumps(tool_call.tool_args),
                        },
                    }
                    for tool_call in content.tool_calls
                ]
            messages.append(message)
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unexpected_chat_log_content",
                translation_placeholders={"type": type(content).__name__},
            )

    return messages


async def _transform_stream(  # noqa: C901
    chat_log: conversation.ChatLog,
    stream: Any,
    *,
    output_tool: str | None,
) -> AsyncIterator[dict[str, Any]]:
    """Transform an OpenAI Chat Completions stream into HA delta dicts.

    Tool-call arguments arrive as incremental JSON fragments across chunks
    (keyed by ``index``); they are accumulated and flushed as a single
    ``tool_calls`` delta when the stream signals completion. The transformer
    tolerates servers that omit ``delta.role`` or ``finish_reason``.

    ``output_tool`` is required by the ``make_transformer`` interface contract
    but unused here: structured output is handled natively via ``response_format``
    (see ``build_request``), so there is no forced-tool delta to extract.
    """
    tool_buffers: dict[int, dict[str, str]] = {}
    last_role: str | None = None

    async for chunk in stream:
        LOGGER.debug("Received chunk: %s", chunk)

        # The final chunk (when stream_options.include_usage is set) carries
        # token usage and has no choices.
        usage = getattr(chunk, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
            chat_log.async_trace(
                {
                    "stats": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                    }
                }
            )
            continue

        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        choice = choices[0]
        delta = choice.delta

        role = getattr(delta, "role", None)
        if role == "assistant" and last_role != "assistant":
            yield {"role": "assistant"}
            last_role = "assistant"

        text = getattr(delta, "content", None)
        if text:
            if last_role != "assistant":
                yield {"role": "assistant"}
                last_role = "assistant"
            yield {"content": text}

        tool_calls = getattr(delta, "tool_calls", None)
        if tool_calls:
            for tool_call in tool_calls:
                index = tool_call.index
                buf = tool_buffers.setdefault(
                    index, {"id": "", "name": "", "arguments": ""}
                )
                if getattr(tool_call, "id", None):
                    buf["id"] = tool_call.id
                function = getattr(tool_call, "function", None)
                if function is not None:
                    if getattr(function, "name", None):
                        buf["name"] = function.name
                    if getattr(function, "arguments", None):
                        buf["arguments"] += function.arguments

        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason and tool_buffers:
            if last_role != "assistant":
                yield {"role": "assistant"}
                last_role = "assistant"
            for index in sorted(tool_buffers):
                buf = tool_buffers[index]
                tool_args = json.loads(buf["arguments"]) if buf["arguments"] else {}
                yield {
                    "tool_calls": [
                        llm.ToolInput(
                            id=buf["id"],
                            tool_name=buf["name"],
                            tool_args=tool_args,
                        )
                    ]
                }
            tool_buffers = {}
            last_role = "tool_result"

    # Flush any tool calls a server signaled only via stream end.
    if tool_buffers:
        if last_role != "assistant":
            yield {"role": "assistant"}
        for index in sorted(tool_buffers):
            buf = tool_buffers[index]
            tool_args = json.loads(buf["arguments"]) if buf["arguments"] else {}
            yield {
                "tool_calls": [
                    llm.ToolInput(
                        id=buf["id"], tool_name=buf["name"], tool_args=tool_args
                    )
                ]
            }


class OpenAIChatProvider(LLMProvider):
    """OpenAI Chat Completions backend."""

    key = "openai"
    default_base_url = "https://api.openai.com/v1"

    def build_client(
        self, hass: HomeAssistant, api_key: str, base_url: str
    ) -> openai.AsyncOpenAI:
        """Construct the OpenAI async client."""
        return openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=get_async_client(hass),
        )

    def categorize_error(self, err: Exception) -> ProviderError:
        """Classify an OpenAI SDK exception."""
        if isinstance(err, openai.AuthenticationError):
            return ProviderError.AUTH
        if isinstance(err, openai.APITimeoutError):
            return ProviderError.TIMEOUT
        if isinstance(err, openai.APIConnectionError):
            return ProviderError.CONNECTION
        return ProviderError.OTHER

    def normalize_model(self, raw: Any) -> ModelInfo:
        """Normalize an OpenAI ``Model`` into a :class:`ModelInfo` descriptor."""
        created = getattr(raw, "created", None)
        return ModelInfo(
            type="model",
            id=raw.id,
            created_at=(
                datetime.fromtimestamp(created, UTC)
                if created
                else datetime(1970, 1, 1, tzinfo=UTC)
            ),
            display_name=raw.id,
        )

    async def async_list_models(self, client: openai.AsyncOpenAI) -> list[ModelInfo]:
        """Fetch the model list, raising HA-level exceptions on failure."""
        try:
            result = await client.with_options(timeout=10.0).models.list()
        except openai.APIError as err:
            message = getattr(err, "message", None) or str(err)
            category = self.categorize_error(err)
            if category is ProviderError.AUTH:
                raise ConfigEntryAuthFailed(
                    translation_domain=DOMAIN,
                    translation_key="api_authentication_error",
                    translation_placeholders={"message": message},
                ) from err
            if category is ProviderError.TIMEOUT:
                raise TimeoutError(message) from err
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"message": message},
            ) from err
        return [self.normalize_model(model) for model in result.data]

    def defaults(self) -> dict[str, Any]:
        """OpenAI Chat Completions default options."""
        return DEFAULT_OPENAI

    async def fetch_model(
        self, coordinator: ConfigurableLLMCoordinator, model_id: str
    ) -> tuple[ModelInfo | None, str | None, str | None]:
        """Resolve a model id, accepting anything for compatible/local servers.

        OpenAI-compatible ``/v1/models/{id}`` is often unimplemented by local
        servers, which also use arbitrary model ids — so any failure degrades
        gracefully to accepting the id rather than blocking setup.
        """
        try:
            model = await coordinator.client.with_options(timeout=10.0).models.retrieve(
                model_id
            )
        except Exception:  # noqa: BLE001 - lenient: never block setup
            return (
                ModelInfo(
                    type="model",
                    id=model_id,
                    created_at=datetime(1970, 1, 1, tzinfo=UTC),
                    display_name=model_id,
                ),
                None,
                None,
            )
        return self.normalize_model(model), None, None

    async def build_request(
        self, ctx: ProviderRequestContext
    ) -> tuple[dict[str, Any], str | None]:
        """Build the Chat Completions request kwargs for one turn."""
        options = ctx.options
        structure_name = ctx.structure_name

        system = ctx.chat_log.content[0]
        if not isinstance(system, conversation.SystemContent):
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="system_message_not_found"
            )

        # Chat Completions carries the system prompt as the first message.
        messages: list[dict[str, Any]] = [{"role": "system", "content": system.content}]
        messages.extend(_convert_content(ctx.chat_log.content[1:]))

        request: dict[str, Any] = {
            "model": ctx.model.id,
            "messages": messages,
            "max_tokens": options[CONF_MAX_TOKENS],
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        temperature = options.get(CONF_TEMPERATURE)
        if temperature is not None:
            request["temperature"] = temperature
        top_p = options.get(CONF_TOP_P)
        if top_p is not None:
            request["top_p"] = top_p

        # reasoning_effort is model-dependent; only send when explicitly set.
        reasoning_effort = options.get(CONF_REASONING_EFFORT)
        if reasoning_effort and reasoning_effort != "none":
            request["reasoning_effort"] = reasoning_effort

        tools: list[dict[str, Any]] = []
        if ctx.chat_log.llm_api:
            tools = [
                _format_tool(tool, ctx.chat_log.llm_api.custom_serializer)
                for tool in ctx.chat_log.llm_api.tools
            ]

        # Handle image attachments by adding them to the last user message.
        last_content = ctx.chat_log.content[-1]
        if last_content.role == "user" and last_content.attachments:
            last_message = messages[-1]
            if last_message.get("role") != "user":
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="user_message_not_found",
                )
            if isinstance(last_message["content"], str):
                last_message["content"] = [
                    {"type": "text", "text": last_message["content"]}
                ]
            last_message["content"].extend(
                cast(
                    list[dict[str, Any]],
                    await self.prepare_files(
                        ctx.hass,
                        ctx.model,
                        [(a.path, a.mime_type) for a in last_content.attachments],
                    ),
                )
            )

        # Structured output: native json_schema response_format (widely supported
        # by OpenAI, vLLM guided decoding, Ollama format=json_schema).
        if ctx.structure and structure_name:
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": slugify(structure_name),
                    "schema": _format_structured_output(
                        ctx.structure, ctx.chat_log.llm_api
                    ),
                    "strict": True,
                },
            }
            structure_name = None

        if tools:
            request["tools"] = tools

        return request, structure_name

    async def create_stream(
        self, client: openai.AsyncOpenAI, request_kwargs: dict[str, Any]
    ) -> Any:
        """Issue the streaming Chat Completions request."""
        return await client.chat.completions.create(**request_kwargs)

    def make_transformer(
        self,
        chat_log: conversation.ChatLog,
        stream: Any,
        *,
        output_tool: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Wrap the raw Chat Completions stream with the delta converter."""
        return _transform_stream(chat_log, stream, output_tool=output_tool)

    def convert_back(
        self, chat_content: Iterable[conversation.Content]
    ) -> tuple[list[dict[str, Any]], None]:
        """Convert HA chat content into Chat Completions messages (no state)."""
        return _convert_content(chat_content), None

    async def prepare_files(
        self,
        hass: HomeAssistant,
        model: ModelInfo,
        files: list[tuple[Path, str | None]],
    ) -> Iterable[dict[str, Any]]:
        """Build Chat Completions image attachment blocks (images only).

        Vanilla Chat Completions has no document/PDF block; PDFs are rejected.
        """

        def append_files_to_content() -> list[dict[str, Any]]:
            content: list[dict[str, Any]] = []

            for file_path, mime_type in files:
                if not file_path.exists():
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="wrong_file_path",
                        translation_placeholders={"file_path": file_path.as_posix()},
                    )

                if mime_type is None:
                    mime_type = guess_file_type(file_path)[0]

                if not mime_type or not mime_type.startswith("image/"):
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="wrong_file_type",
                        translation_placeholders={
                            "file_path": file_path.as_posix(),
                            "mime_type": mime_type or "unknown",
                            "model": model.display_name,
                        },
                    )
                if mime_type == "image/jpg":
                    mime_type = "image/jpeg"

                base64_file = base64.b64encode(file_path.read_bytes()).decode("utf-8")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_file}"
                        },
                    }
                )

            return content

        return await hass.async_add_executor_job(append_files_to_content)

    def diagnostics_metadata(self) -> dict[str, str]:
        """OpenAI SDK info for the diagnostics dump."""
        return {"client": f"openai=={openai.__version__}"}
