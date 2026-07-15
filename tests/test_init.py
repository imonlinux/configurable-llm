"""Test the Configurable LLM init module."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.configurable_llm import (
    DOMAIN,
    PLATFORMS,
    async_migrate_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    async_update_options,
)
from custom_components.configurable_llm.const import CONF_PROTOCOL, PROTOCOL_ANTHROPIC


async def test_async_setup(hass: HomeAssistant) -> None:
    """Test async_setup."""
    result = await async_setup(hass, {})
    assert result is True


@pytest.mark.skip("Requires integration to be registered in HA")
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_anthropic_client: MagicMock,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test async_setup_entry."""
    mock_config_entry.runtime_data = None
    mock_config_entry.subentries = {}

    with patch(
        "custom_components.configurable_llm.providers.anthropic_provider"
        ".anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.runtime_data is not None
    assert mock_config_entry.runtime_data.data == mock_models_list

    # Verify platforms were forwarded
    for platform in PLATFORMS:
        hass.config_entries.async_forward_entry_setups.assert_any_call(
            mock_config_entry, [platform]
        )


@pytest.mark.skip("Requires integration to be registered in HA")
async def test_async_setup_entry_with_deprecated_model(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_anthropic_client: MagicMock,
) -> None:
    """Test async_setup_entry creates repair issue for deprecated models."""
    from anthropic.resources.messages.messages import DEPRECATED_MODELS

    if not DEPRECATED_MODELS:
        pytest.skip("No deprecated models to test")

    deprecated_model = list(DEPRECATED_MODELS)[0]
    mock_subentry = MagicMock()
    mock_subentry.data = {"chat_model": deprecated_model}
    mock_config_entry.subentries = {"test_subentry": mock_subentry}
    mock_config_entry.runtime_data = None

    with patch(
        "custom_components.configurable_llm.providers.anthropic_provider"
        ".anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ), patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_create_issue:
        await async_setup_entry(hass, mock_config_entry)

        mock_create_issue.assert_called_once()
        call_kwargs = mock_create_issue.call_args.kwargs
        assert call_kwargs["translation_key"] == "model_deprecated"
        assert call_kwargs["is_fixable"] is True


async def test_async_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test async_unload_entry."""
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once_with(
        mock_config_entry, PLATFORMS
    )


async def test_async_update_options(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test async_update_options."""
    hass.config_entries.async_reload = AsyncMock()

    await async_update_options(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_called_once_with(
        mock_config_entry.entry_id
    )


async def test_async_migrate_entry_v1_to_v2(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test migration from v1 to v2 adds protocol: anthropic.

    Regression test for CRITICAL-1: v1 entries must migrate to v2 with
    protocol stamped, otherwise HA sets MIGRATION_ERROR and integration
    fails to load.
    """
    # Set up a v1 entry (pre-1.2.0, no protocol field)
    mock_config_entry.version = 1
    mock_config_entry.data = {"api_key": "sk-ant-test1234"}

    hass.config_entries.async_update_entry = MagicMock()

    result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = hass.config_entries.async_update_entry.call_args.kwargs
    assert call_kwargs["version"] == 2
    assert call_kwargs["data"][CONF_PROTOCOL] == PROTOCOL_ANTHROPIC


async def test_async_migrate_entry_v2_noop(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test migration from v2 is a no-op."""
    mock_config_entry.version = 2
    mock_config_entry.data = {
        "api_key": "sk-ant-test1234",
        CONF_PROTOCOL: PROTOCOL_ANTHROPIC,
    }

    result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    hass.config_entries.async_update_entry.assert_not_called()
