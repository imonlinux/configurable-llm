# Changelog

All notable changes to this project are documented here. This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.1.3

### Fixed

- **Integration failed to load on Home Assistant 2025.8** — Added `from __future__ import annotations` to `entity.py`. The module used `conversation.ToolResultContentDeltaDict` in type annotations, but that symbol does not exist in Home Assistant 2025.8 (the integration's minimum supported version); without deferred annotations it was evaluated at import time and raised `AttributeError`, preventing the conversation and AI Task platforms from loading. This is the same class of fix applied to `ai_task.py` in 1.1.2.
- **Config flow help text cleaned up** — Reworded the base URL field description to remove embedded example URLs (which are not permitted in translation strings), pointing to the documentation for provider-specific URLs instead. Provider examples remain available in `docs/PROVIDERS.md`.

### Changed

- Added a Hassfest validation workflow and updated GitHub Actions to current versions (Node 24 compatible). CI now runs the test suite, HACS validation, and Hassfest. Repository/CI changes only; not part of the installed integration.

## 1.1.2

### Fixed

- **AI Task platform failed to load** — Added `from __future__ import annotations` to `ai_task.py`. The module annotated a function with `ConfigurableLLMConfigEntry`, which is imported only under `TYPE_CHECKING`; without deferred annotations the name was evaluated at import time and raised `NameError`, preventing the AI Task platform from loading on Home Assistant.

### Added

- Unit test suite covering the conversation, AI task, config flow, coordinator, and entity modules, plus a GitHub Actions workflow running the tests (Python 3.13) and HACS validation. Test-only changes; not part of the installed integration.

## 1.1.1

### Added

- custom_components/configurable_llm/brand/icon.png

## 1.1.0

### Fixed

- **Repairs flow crash** — Restored None-guard in `async_step_init` to handle HA's initial form render call without AttributeError
- **Silent citation loss** — Restored full citation handling via `citation.to_dict()` instead of only `CitationsWebSearchResultLocation`
- **LiteLLM model bug** — Runtime requests now use `self.model_info.id` instead of falling back to hardcoded Anthropic ID in recommended mode
- **Init fallback routing** — Model initialization now uses `coordinator.get_default_model()` instead of hardcoded Anthropic ID
- Added `PARALLEL_UPDATES = 0` to conversation and AI task platforms for unrestricted concurrent entity operations

## 1.0.9

### Removed

- Removed the quality_scale declaration from manifest.json and deleted quality_scale.yaml. The quality scale is a Home Assistant Core concept tied to the official integration review process; self-declaring it on a HACS-custom integration is not meaningful and the inherited values did not accurately reflect this fork.

## 1.0.8

### Changed

- Documentation overhaul. Consolidated `README.md`, `INSTALL.md`, `EXAMPLES.md`, and `COMPONENT_SUMMARY.md` into a streamlined `README.md` plus a separate `docs/PROVIDERS.md` for provider-specific setup. Added screenshots of the setup form and model options. Updated `hacs.json` to reflect the actual minimum Home Assistant version (2025.8).

## 1.0.7

### Changed

- `CONF_PROMPT` is now imported from `homeassistant.const` instead of being defined locally, matching upstream Anthropic. The stored value is unchanged (`"prompt"`) so existing config entries continue to work without migration.

## 1.0.6

### Added

- Model-specific options page now includes an inline note explaining that tool features (web search, web fetch, code execution) may not be implemented by every provider and may produce a runtime error if enabled on an unsupported provider.

## 1.0.5

### Changed

- Pinned the `anthropic` Python SDK to `==0.96.0` (in both `manifest.json` and `requirements.txt`). The previous loose `>=0.40.0` allowed pip to install pre-feature SDK versions that lack the type imports the integration uses, causing the integration to fail to load. This matches the pin in upstream Home Assistant.

## 1.0.4

### Added

- Web fetch tool support (`web_fetch_20250910` and `web_fetch_20260209`), matching upstream Anthropic. New configuration options:
  - **Web fetch** — toggle to allow the model to retrieve full content from URLs and PDFs
  - **Maximum web fetches** — cap on fetches per response
- New translation strings for the web fetch fields in both the conversation and AI task subentries.

## 1.0.3

### Changed

- Default model selection now uses the first model returned by the provider's `/v1/models` endpoint instead of the hardcoded `claude-3-5-haiku-20241022`. This makes the integration work out of the box with non-Anthropic providers whose model IDs differ. The Anthropic ID remains the fallback for providers that don't expose a usable model list.
- The same logic now applies to the location-resolution call used when web search + "include home location" is enabled, so geolocation works on providers using non-Anthropic model IDs.

## 1.0.2

### Added

- `after_dependencies: ["assist_pipeline", "intent"]` and `dependencies: ["conversation"]` in `manifest.json` so the integration loads in the right order relative to the conversation platform.

### Fixed

- `iot_class` corrected from `cloud_poll` to the valid value `cloud_polling`.

### Changed

- Quality scale lowered from `platinum` to `silver` to reflect the realistic state of the integration (no test suite or strict type-checking yet).

## 1.0.1

### Fixed

- **Configuration UI showed raw translation keys (e.g., `prompt`, `llm_hass_api`) instead of human-readable labels.** Added `translations/en.json` with all strings fully resolved. Home Assistant doesn't process `strings.json` for custom integrations — only the file under `translations/` — and the previous version's `[%key:...%]` placeholders in `strings.json` were never being resolved at runtime.
- Removed unnecessary deviations in `config_flow.py` from upstream Anthropic patterns (extra exception branches, fallback model fabrication, etc.) that didn't add value over what upstream already does correctly.
- Added a proper `async_step_reauth` / `async_step_reauth_confirm` flow that preserves the configured base URL across reauthentication.

## 1.0.0

### Added

- Initial release. Fork of the Home Assistant Anthropic integration with a configurable API base URL field added to the setup form, allowing the integration to be used with any Anthropic-compatible API endpoint.
