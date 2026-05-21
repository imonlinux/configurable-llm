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
CONF_WEB_FETCH_MAX_USES = "web_fetch_max_uses"
CONF_WEB_SEARCH = "web_search"
CONF_WEB_SEARCH_USER_LOCATION = "user_location"
CONF_WEB_SEARCH_MAX_USES = "web_search_max_uses"
CONF_WEB_SEARCH_CITY = "city"
CONF_WEB_SEARCH_REGION = "region"
CONF_WEB_SEARCH_COUNTRY = "country"
CONF_WEB_SEARCH_TIMEZONE = "timezone"
CONF_BASE_URL = "base_url"

DEFAULT_BASE_URL = "https://api.anthropic.com"


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

TOOL_SEARCH_UNSUPPORTED_MODELS = [
    "claude-haiku",
]
