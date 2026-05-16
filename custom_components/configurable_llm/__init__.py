"""The Configurable LLM integration."""

from anthropic.resources.messages.messages import DEPRECATED_MODELS

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.typing import ConfigType

from .const import CONF_CHAT_MODEL, DEFAULT_CONVERSATION_NAME, DOMAIN, LOGGER
from .coordinator import ConfigurableLLMConfigEntry, ConfigurableLLMCoordinator

PLATFORMS = (Platform.AI_TASK, Platform.CONVERSATION)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Configurable LLM."""
    await async_migrate_integration(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigurableLLMConfigEntry) -> bool:
    """Set up Configurable LLM from a config entry."""
    coordinator = ConfigurableLLMCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    LOGGER.debug("Available models: %s", coordinator.data)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    for subentry in entry.subentries.values():
        if (model := subentry.data.get(CONF_CHAT_MODEL)) and model in DEPRECATED_MODELS:
            ir.async_create_issue(
                hass,
                DOMAIN,
                "model_deprecated",
                is_fixable=True,
                is_persistent=False,
                learn_more_url="https://platform.claude.com/docs/en/about-claude/model-deprecations",
                severity=ir.IssueSeverity.WARNING,
                translation_key="model_deprecated",
            )
            break

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigurableLLMConfigEntry) -> bool:
    """Unload Configurable LLM."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(
    hass: HomeAssistant, entry: ConfigurableLLMConfigEntry
) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_integration(hass: HomeAssistant) -> None:
    """Migrate integration entry structure."""

    # Make sure we get enabled config entries first
    entries = sorted(
        hass.config_entries.async_entries(DOMAIN),
        key=lambda e: e.disabled_by is not None,
    )
    if not any(entry.version == 1 for entry in entries):
        return

    api_keys_entries: dict[str, tuple[ConfigurableLLMConfigEntry, bool]] = {}
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    for entry in entries:
        use_existing = False
        subentry = ConfigSubentry(
            data=entry.options,
            subentry_type="conversation",
            title=entry.title,
            unique_id=None,
        )
        if entry.data[CONF_API_KEY] not in api_keys_entries:
            use_existing = True
            all_disabled = all(
                e.disabled_by is not None
                for e in entries
                if e.data[CONF_API_KEY] == entry.data[CONF_API_KEY]
            )
            api_keys_entries[entry.data[CONF_API_KEY]] = (entry, all_disabled)

    # Migration logic would go here for future versions
