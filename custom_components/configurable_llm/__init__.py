"""The Configurable LLM integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import CONF_CHAT_MODEL, DOMAIN, LOGGER
from .coordinator import (
    ConfigurableLLMConfigEntry,
    ConfigurableLLMCoordinator,
)

PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Configurable LLM."""
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigurableLLMConfigEntry
) -> bool:
    """Set up Configurable LLM from a config entry."""
    coordinator = ConfigurableLLMCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    LOGGER.debug("Available models: %s", coordinator.data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Surface a repair issue if any subentry is using a deprecated model.
    for subentry in entry.subentries.values():
        model = subentry.data.get(CONF_CHAT_MODEL)
        if model and coordinator.provider.is_model_deprecated(model):
            ir.async_create_issue(
                hass,
                DOMAIN,
                "model_deprecated",
                is_fixable=True,
                is_persistent=False,
                learn_more_url=(
                    "https://platform.claude.com/docs/en/about-claude/"
                    "model-deprecations"
                ),
                severity=ir.IssueSeverity.WARNING,
                translation_key="model_deprecated",
            )
            break

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigurableLLMConfigEntry
) -> bool:
    """Unload Configurable LLM."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(
    hass: HomeAssistant, entry: ConfigurableLLMConfigEntry
) -> None:
    """Reload entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
