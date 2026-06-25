"""Base entity for Configurable LLM."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigSubentry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHAT_MODEL, DEFAULT, DOMAIN, LOGGER
from .coordinator import ConfigurableLLMConfigEntry, ConfigurableLLMCoordinator
from .providers import ProviderError, ProviderRequestContext

# Max number of back and forth with the LLM to generate a response
MAX_TOOL_ITERATIONS = 10


class ConfigurableLLMBaseEntity(CoordinatorEntity[ConfigurableLLMCoordinator]):
    """Protocol-agnostic base LLM entity.

    Owns the HA-facing shell and the (protocol-agnostic) tool-loop; every
    protocol-specific step is delegated to the entry's provider
    (``self.coordinator.provider``).
    """

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, entry: ConfigurableLLMConfigEntry, subentry: ConfigSubentry
    ) -> None:
        """Initialize the entity."""
        super().__init__(entry.runtime_data)
        self.entry = entry
        self.subentry = subentry
        coordinator = entry.runtime_data
        self.model_info, _ = coordinator.get_model_info(
            subentry.data.get(
                CONF_CHAT_MODEL,
                coordinator.get_default_model(DEFAULT[CONF_CHAT_MODEL]),
            )
        )
        self._attr_unique_id = subentry.subentry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="Configurable LLM",
            model=self.model_info.display_name,
            model_id=self.model_info.id,
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    async def _async_handle_chat_log(  # noqa: C901
        self,
        chat_log: conversation.ChatLog,
        structure_name: str | None = None,
        structure: vol.Schema | None = None,
        max_iterations: int = MAX_TOOL_ITERATIONS,
    ) -> None:
        """Generate an answer for the chat log.

        The loop body is protocol-agnostic: it builds a provider request,
        streams the response into the chat log, converts the produced deltas
        back into provider messages for the next turn, and maps any provider
        error to a coordinator side-effect + translation key.
        """
        provider = self.coordinator.provider
        client = self.coordinator.client

        ctx = ProviderRequestContext(
            hass=self.hass,
            chat_log=chat_log,
            model=self.model_info,
            options=DEFAULT | self.subentry.data,
            structure_name=structure_name,
            structure=structure,
        )
        request_kwargs, structure_name = await provider.build_request(ctx)

        # To prevent infinite loops, we limit the number of iterations
        for _iteration in range(max_iterations):
            try:
                stream = await provider.create_stream(client, request_kwargs)

                new_messages, state = provider.convert_back(
                    [
                        content
                        async for content in chat_log.async_add_delta_content_stream(
                            self.entity_id,
                            provider.make_transformer(
                                chat_log,
                                stream,
                                output_tool=structure_name or None,
                            ),
                        )
                    ]
                )
                request_kwargs = provider.merge_iteration_state(
                    request_kwargs, new_messages, state
                )
            except HomeAssistantError:
                # Provider-internal control-flow errors (e.g. api_refusal) and
                # validation errors must surface unchanged, not be re-mapped.
                raise
            except Exception as err:
                category = provider.categorize_error(err)
                message = getattr(err, "message", None) or str(err)
                if category is ProviderError.AUTH:
                    # Trigger coordinator to confirm the auth failure
                    # and trigger the reauth flow.
                    await self.coordinator.async_request_refresh()
                    translation_key = "api_authentication_error"
                elif category in (ProviderError.CONNECTION, ProviderError.TIMEOUT):
                    LOGGER.info("Connection error while talking to API: %s", err)
                    self.coordinator.mark_connection_error()
                    translation_key = "api_error"
                else:
                    # Non-connection error, mark connection as healthy
                    self.coordinator.async_set_updated_data(self.coordinator.data)
                    translation_key = "api_error"
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key=translation_key,
                    translation_placeholders={"message": message},
                ) from err

            if not chat_log.unresponded_tool_results:
                self.coordinator.async_set_updated_data(self.coordinator.data)
                break
