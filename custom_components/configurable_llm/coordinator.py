"""Coordinator for the Configurable LLM integration."""

from __future__ import annotations

import datetime
from typing import Any

from anthropic.types import ModelInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_BASE_URL, CONF_PROTOCOL, LOGGER
from .providers import LLMProvider, get_provider

UPDATE_INTERVAL_CONNECTED = datetime.timedelta(hours=12)
UPDATE_INTERVAL_DISCONNECTED = datetime.timedelta(minutes=1)

type ConfigurableLLMConfigEntry = ConfigEntry[ConfigurableLLMCoordinator]


class ConfigurableLLMCoordinator(DataUpdateCoordinator[list[ModelInfo]]):
    """Coordinator using different intervals after success and failure."""

    client: Any
    provider: LLMProvider

    def __init__(self, hass: HomeAssistant, config_entry: ConfigurableLLMConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=UPDATE_INTERVAL_CONNECTED,
            update_method=self.async_update_data,
            always_update=False,
        )

        # Resolve the provider from the entry's protocol and build its client.
        # ``CONF_PROTOCOL`` defaults to Anthropic for pre-migration entries.
        self.provider = get_provider(config_entry.data.get(CONF_PROTOCOL))
        base_url = config_entry.data.get(CONF_BASE_URL, self.provider.default_base_url)
        self.client = self.provider.build_client(
            hass,
            config_entry.data[CONF_API_KEY],
            base_url,
        )

    @callback
    def async_set_updated_data(self, data: list[ModelInfo]) -> None:
        """Manually update data, notify listeners and update refresh interval."""
        self.update_interval = UPDATE_INTERVAL_CONNECTED
        super().async_set_updated_data(data)

    async def async_update_data(self) -> list[ModelInfo]:
        """Fetch data from the API.

        The provider raises ``ConfigEntryAuthFailed`` / ``TimeoutError`` /
        ``UpdateFailed`` (mapped from its SDK), which the
        ``DataUpdateCoordinator`` machinery handles.
        """
        self.update_interval = UPDATE_INTERVAL_DISCONNECTED
        result = await self.provider.async_list_models(self.client)
        self.update_interval = UPDATE_INTERVAL_CONNECTED
        return result

    def mark_connection_error(self) -> None:
        """Mark the connection as having an error and reschedule background check."""
        self.update_interval = UPDATE_INTERVAL_DISCONNECTED
        if self.last_update_success:
            self.last_update_success = False
            self.async_update_listeners()
            if self._listeners and not self.hass.is_stopping:
                self._schedule_refresh()

    @callback
    def get_model_info(self, model_id: str) -> tuple[ModelInfo, bool]:
        """Get model info for a given model ID."""
        # First try: exact name match
        for model in self.data or []:
            if model.id == model_id:
                return model, True
        # Second try: match by alias
        alias = self.provider.model_alias(model_id)
        for model in self.data or []:
            if self.provider.model_alias(model.id) == alias:
                return model, True
        # Model not found, return safe defaults
        return ModelInfo(
            type="model",
            id=model_id,
            created_at=datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC),
            display_name=alias,
        ), False

    @callback
    def get_default_model(self, fallback: str) -> str:
        """Return a sensible default model ID for this provider.

        Uses the first model returned by the provider's model list when
        available. This makes the integration work out of the box with
        non-Anthropic providers (z.ai, local servers, etc.) whose model IDs
        differ from Anthropic's. Falls back to the supplied `fallback` value
        when the provider does not expose a usable model list.
        """
        return self.provider.get_default_model(self.data, fallback)
