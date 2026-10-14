"""HA-version compatibility helpers for chat-log tool results.

Home Assistant 2026.10 deprecated ``ToolResultContent.tool_result`` (a plain
JSON object) in favor of ``ToolResultContent.result``, an ``llm.ToolResult``
carrying the tool's ``data`` and an ``error`` flag. Reading the old field and
emitting the old ``tool_result`` delta key keep working on 2026.10 with a
warning until HA 2027.11. Older cores this integration supports only have the
old field, so these helpers pick the right shape at runtime and one release
serves both.
"""

from __future__ import annotations

from typing import Any, cast

from homeassistant.components import conversation
from homeassistant.helpers import llm

HAS_LLM_TOOL_RESULT = hasattr(llm, "ToolResult")
"""True when this HA version exposes ``llm.ToolResult`` (2026.10+)."""


def tool_result_payload(
    content: conversation.ToolResultContent,
) -> tuple[Any, bool | None]:
    """Return ``(payload, error)`` for a chat-log tool result.

    Prefers the 2026.10+ ``result`` field (an ``llm.ToolResult``); falls back
    to the legacy ``tool_result`` object on older cores, where the error flag
    does not exist (``None``).
    """
    result = getattr(content, "result", None)
    if result is None:
        return content.tool_result, None
    return result.data, result.error


def tool_result_delta(
    role: str,
    tool_call_id: str,
    tool_name: str,
    data: Any,
    error: bool,
) -> conversation.ToolResultContentDeltaDict:
    """Build a tool-result delta dict in the shape this HA version expects."""
    if HAS_LLM_TOOL_RESULT:
        return cast(
            "conversation.ToolResultContentDeltaDict",
            {
                "role": role,
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "result": llm.ToolResult(data=data, error=error),  # type: ignore[attr-defined]
            },
        )
    return cast(
        "conversation.ToolResultContentDeltaDict",
        {
            "role": role,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "tool_result": data,
        },
    )
