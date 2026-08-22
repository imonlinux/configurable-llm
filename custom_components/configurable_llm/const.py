"""Constants for the Configurable LLM integration."""

from enum import StrEnum
import logging

DOMAIN = "configurable_llm"
LOGGER = logging.getLogger(__package__)

DEFAULT_CONVERSATION_NAME = "LLM conversation"
DEFAULT_AI_TASK_NAME = "LLM AI Task"

CONF_RECOMMENDED = "recommended"
CONF_CHAT_MODEL = "chat_model"
CONF_CODE_EXECUTION = "code_execution"
CONF_MAX_TOKENS = "max_tokens"
CONF_PROMPT_CACHING = "prompt_caching"
CONF_THINKING_BUDGET = "thinking_budget"
CONF_THINKING_EFFORT = "thinking_effort"
CONF_TOOL_SEARCH = "tool_search"
CONF_WEB_FETCH = "web_fetch"

# OpenAI Chat Completions option names (protocol-specific, mirror core's naming).
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"
CONF_REASONING_EFFORT = "reasoning_effort"

# `reasoning_effort` choices offered for OpenAI-compatible providers. Servers and
# models vary in what they accept; "none" means "do not send the parameter".
REASONING_EFFORT_OPTIONS = ["none", "low", "medium", "high"]

CONF_WEB_FETCH_MAX_USES = "web_fetch_max_uses"
CONF_WEB_SEARCH = "web_search"
CONF_WEB_SEARCH_USER_LOCATION = "user_location"
CONF_WEB_SEARCH_MAX_USES = "web_search_max_uses"
CONF_WEB_SEARCH_CITY = "city"
CONF_WEB_SEARCH_REGION = "region"
CONF_WEB_SEARCH_COUNTRY = "country"
CONF_WEB_SEARCH_TIMEZONE = "timezone"
CONF_BASE_URL = "base_url"

# Entry-level protocol selector: which API contract this endpoint speaks.
# "anthropic" = Anthropic Messages API (also Anthropic-compatible proxies/servers);
# "openai" = OpenAI Chat Completions (also vLLM, Ollama, LM Studio, OpenRouter, ...).
CONF_PROTOCOL = "protocol"
CONF_PRESET = "preset"
PROTOCOL_ANTHROPIC = "anthropic"
PROTOCOL_OPENAI = "openai"
DEFAULT_PROTOCOL = PROTOCOL_ANTHROPIC

DEFAULT_BASE_URL = "https://api.anthropic.com"

# Provider presets: convenience entries that pre-fill protocol + base_url in the
# setup flow. Add a row here to support another OpenAI-compatible host — no code
# change needed elsewhere. ``protocol=None`` (the "custom" preset) means the user
# supplies both protocol and base_url manually.
PRESET_CUSTOM = "custom"
PRESETS: list[dict[str, str | None]] = [
    {"value": "anthropic", "protocol": PROTOCOL_ANTHROPIC, "base_url": "https://api.anthropic.com"},
    {"value": "zai", "protocol": PROTOCOL_ANTHROPIC, "base_url": "https://api.z.ai/api/anthropic"},
    {"value": "openai", "protocol": PROTOCOL_OPENAI, "base_url": "https://api.openai.com/v1"},
    {"value": "openrouter", "protocol": PROTOCOL_OPENAI, "base_url": "https://openrouter.ai/api/v1"},
    {"value": "groq", "protocol": PROTOCOL_OPENAI, "base_url": "https://api.groq.com/openai/v1"},
    {"value": "ollama", "protocol": PROTOCOL_OPENAI, "base_url": "http://localhost:11434/v1"},
    {"value": "lmstudio", "protocol": PROTOCOL_OPENAI, "base_url": "http://localhost:1234/v1"},
    {"value": "custom", "protocol": None, "base_url": None},
]


def get_preset(value: str) -> dict[str, str | None] | None:
    """Look up a preset by its value, or None if not found."""
    for preset in PRESETS:
        if preset["value"] == value:
            return preset
    return None


class PromptCaching(StrEnum):
    """Prompt caching options."""

    OFF = "off"
    PROMPT = "prompt"
    AUTOMATIC = "automatic"


MIN_THINKING_BUDGET = 1024

DEFAULT = {
    CONF_CHAT_MODEL: "claude-3-5-haiku-20241022",  # More widely supported model ID
    CONF_CODE_EXECUTION: False,
    CONF_MAX_TOKENS: 3000,
    CONF_PROMPT_CACHING: PromptCaching.PROMPT.value,
    CONF_THINKING_BUDGET: MIN_THINKING_BUDGET,
    CONF_THINKING_EFFORT: "low",
    CONF_TOOL_SEARCH: False,
    CONF_WEB_FETCH: False,
    CONF_WEB_FETCH_MAX_USES: 5,
    CONF_WEB_SEARCH: False,
    CONF_WEB_SEARCH_USER_LOCATION: False,
    CONF_WEB_SEARCH_MAX_USES: 5,
    CONF_BASE_URL: DEFAULT_BASE_URL,
}

# Defaults for the OpenAI Chat Completions protocol. These are merged onto a
# subentry's data by the OpenAI config-flow schemas; the Anthropic `DEFAULT`
# dict above applies to Anthropic entries.
DEFAULT_OPENAI = {
    CONF_CHAT_MODEL: "gpt-4o-mini",
    CONF_MAX_TOKENS: 3000,
    CONF_TEMPERATURE: 1.0,
    CONF_TOP_P: 1.0,
    CONF_REASONING_EFFORT: "none",
}

TOOL_SEARCH_UNSUPPORTED_MODELS = [
    "claude-haiku",
]
