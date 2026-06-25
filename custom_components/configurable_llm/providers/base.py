"""Provider interface for the Configurable LLM integration.

The integration speaks to LLM endpoints through a pluggable provider. Each
provider encapsulates one API contract (Anthropic Messages, OpenAI Chat
Completions, ...) behind the :class:`LLMProvider` interface so the entity,
coordinator and config flow stay protocol-agnostic.

For this increment the runtime "model descriptor" currency remains
``anthropic.types.ModelInfo`` — both providers normalize their native model
list into it — which bounds the refactor blast radius. A future increment may
introduce a provider-neutral ``ModelDescriptor`` supertype.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from anthropic.types import ModelInfo

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from pathlib import Path

    from ..coordinator import ConfigurableLLMCoordinator

__all__ = ["LLMProvider", "ModelInfo", "ProviderError", "ProviderRequestContext"]


class ProviderError(StrEnum):
    """Coarse category of a provider/SDK error.

    Callers (coordinator poll, config-flow validation, entity chat loop) map
    this category to their own outcome — HA exception, UI error key, or
    translation key + coordinator side-effect — so a single per-provider
    :meth:`LLMProvider.categorize_error` feeds all three.
    """

    AUTH = "auth"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    OTHER = "other"


@dataclass
class ProviderRequestContext:
    """Everything a provider needs to build a request for one chat-log turn.

    Bundles the values that the (former) entity methods read off ``self``, so
    no provider method ever touches an entity instance.
    """

    hass: HomeAssistant
    chat_log: conversation.ChatLog
    model: ModelInfo
    options: dict[str, Any]
    structure_name: str | None
    structure: vol.Schema | None


class LLMProvider(ABC):
    """Protocol-agnostic contract for an LLM API backend.

    Concrete providers (``AnthropicProvider``, ``OpenAIChatProvider``) implement
    the abstract methods; shared defaults (model aliasing, default-model
    resolution, the deprecated-model no-ops) live here.
    """

    #: Stable key stored on the config entry (``data[CONF_PROTOCOL]``).
    key: str
    #: Base URL used when the user does not supply one.
    default_base_url: str

    # ------------------------------------------------------------------ #
    # Client lifecycle
    # ------------------------------------------------------------------ #
    @abstractmethod
    def build_client(
        self, hass: HomeAssistant, api_key: str, base_url: str
    ) -> Any:
        """Construct and return the provider's async client."""

    async def validate_credentials(
        self, hass: HomeAssistant, data: dict[str, Any]
    ) -> None:
        """Probe the endpoint during setup.

        Default implementation builds a client and lists models; the caller
        (config flow) catches raised SDK exceptions and maps them via
        :meth:`categorize_error`. May be overridden.
        """
        client = self.build_client(
            hass,
            data["api_key"],
            data.get("base_url", self.default_base_url),
        )
        await self.async_list_models(client)

    @abstractmethod
    def categorize_error(self, err: Exception) -> ProviderError:
        """Classify a raised SDK exception into a :class:`ProviderError`."""

    # ------------------------------------------------------------------ #
    # Model listing & resolution (coordinator delegates here)
    # ------------------------------------------------------------------ #
    @abstractmethod
    async def async_list_models(self, client: Any) -> list[ModelInfo]:
        """Fetch and normalize the provider's model list.

        Must raise ``ConfigEntryAuthFailed`` / ``TimeoutError`` / ``UpdateFailed``
        (mapped from the SDK via :meth:`categorize_error`) so the
        ``DataUpdateCoordinator`` machinery handles retries correctly.
        """

    def model_alias(self, model_id: str) -> str:
        """Resolve an alias from a versioned model name (default: identity)."""
        return model_id

    def get_default_model(
        self, models: list[ModelInfo] | None, fallback: str
    ) -> str:
        """Return a sensible default model id for this provider."""
        if models:
            return models[0].id
        return fallback

    # ------------------------------------------------------------------ #
    # Chat loop (entity delegates the five protocol-specific steps)
    # ------------------------------------------------------------------ #
    @abstractmethod
    async def build_request(
        self, ctx: ProviderRequestContext
    ) -> tuple[dict[str, Any], str | None]:
        """Build the provider request kwargs for one turn.

        Returns ``(request_kwargs, effective_structure_name)``. Replaces the
        former ``entity._get_model_args``; reads only from ``ctx``.
        """

    @abstractmethod
    async def create_stream(self, client: Any, request_kwargs: dict[str, Any]) -> Any:
        """Issue the streaming request and return the raw provider stream."""

    @abstractmethod
    def make_transformer(
        self,
        chat_log: conversation.ChatLog,
        stream: Any,
        *,
        output_tool: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Wrap a raw stream with the delta -> HA delta-dict converter."""

    @abstractmethod
    def convert_back(
        self, chat_content: Iterable[conversation.Content]
    ) -> tuple[list[Any], Any]:
        """Convert HA chat content into the provider's native messages.

        Returns ``(messages, state)`` where ``state`` is provider-specific
        round-trip data carried to the next iteration (e.g. Anthropic container
        id; ``None`` for providers without such state).
        """

    def merge_iteration_state(
        self,
        request_kwargs: dict[str, Any],
        new_messages: list[Any],
        state: Any,
    ) -> dict[str, Any]:
        """Fold one iteration's produced messages back into the request.

        Default appends to ``messages`` and ignores ``state``; providers with
        extra iteration state (Anthropic ``container``) override.
        """
        request_kwargs["messages"].extend(new_messages)
        return request_kwargs

    @abstractmethod
    async def prepare_files(
        self,
        hass: HomeAssistant,
        model: ModelInfo,
        files: list[tuple[Path, str | None]],
    ) -> Iterable[Any]:
        """Build provider-native attachment blocks for the given files."""

    @abstractmethod
    async def fetch_model(
        self, coordinator: ConfigurableLLMCoordinator, model_id: str
    ) -> tuple[ModelInfo | None, str | None, str | None]:
        """Resolve a model id chosen in the flow that isn't in the cached list.

        Returns ``(model_info_or_None, error_key_or_None, error_message_or_None)``.
        ``error_key`` is a flow error id (e.g. ``"model_not_found"``); when set
        the caller surfaces it on the model picker.
        """

    # ------------------------------------------------------------------ #
    # Repairs & diagnostics
    # ------------------------------------------------------------------ #
    def deprecated_models(self) -> dict[str, str]:
        """Mapping of deprecated model id -> suggested replacement (default: none)."""
        return {}

    def is_model_deprecated(self, model_id: str) -> bool:
        """Whether a model id is deprecated (default: never)."""
        return False

    def suggest_replacement_family(self, model_id: str) -> str:
        """Suggested replacement family for a deprecated model (default: empty)."""
        return ""

    @abstractmethod
    def diagnostics_metadata(self) -> dict[str, str]:
        """Provider info for the diagnostics dump, e.g. client SDK version."""
