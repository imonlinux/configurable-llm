"""Provider registry for Configurable LLM.

Each supported API contract is registered here under its protocol key
(``data[CONF_PROTOCOL]``). The entity, coordinator and config flow resolve the
active provider for a config entry via :func:`get_provider` and stay agnostic to
which backend is in use.
"""

from __future__ import annotations

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider, ModelInfo, ProviderError, ProviderRequestContext
from .openai_chat_provider import OpenAIChatProvider
from ..const import DEFAULT_PROTOCOL, PROTOCOL_ANTHROPIC, PROTOCOL_OPENAI

__all__ = [
    "AnthropicProvider",
    "LLMProvider",
    "ModelInfo",
    "OpenAIChatProvider",
    "ProviderError",
    "ProviderRequestContext",
    "get_provider",
]

_PROVIDERS: dict[str, LLMProvider] = {
    PROTOCOL_ANTHROPIC: AnthropicProvider(),
    PROTOCOL_OPENAI: OpenAIChatProvider(),
}


def get_provider(key: str | None) -> LLMProvider:
    """Return the provider instance for a protocol key.

    Falls back to the default protocol for unknown/missing keys (e.g.
    pre-migration entries).
    """
    if key is None or key not in _PROVIDERS:
        return _PROVIDERS[DEFAULT_PROTOCOL]
    return _PROVIDERS[key]
