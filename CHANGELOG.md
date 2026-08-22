# Changelog

All notable changes to this project are documented here. This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.2.0-beta.6

Pre-release: two-step configuration flow with preset endpoint preview.

### Changed

- **Configuration flow split into two steps** — Setup now separates preset/API key entry from endpoint confirmation:
  - Step 1: Select provider preset and enter API key
  - Step 2: Review and confirm pre-filled protocol and base URL (editable)
- **Config flow minor version bumped to 2** — Triggers reconfiguration for existing entries

### Fixed

- **Preset values now visible before submission** — When selecting a provider preset (z.ai, OpenRouter, Ollama, etc.), the corresponding protocol and base URL are now displayed in a confirmation step before the entry is created, allowing users to verify and edit the values
- **Reauth bypasses endpoint step** — Reauthentication flow streamlined to single step (API key only), preserving existing entry endpoint

## 1.2.0-beta.5

Pre-release: HACS compliance and UX improvements.

### Changed

- **Dependency version constraints for HACS compliance** — Changed `anthropic==0.108.0` to `anthropic>=0.108.0` and `openai==2.45.0` to `openai>=2.45.0` in manifest.json. Uses minimum version constraints instead of exact pins to avoid forcing Home Assistant core to downgrade packages it already ships. Maintains compatibility while allowing HA to manage its own dependency tree.

### Added

- **Enhanced configuration form UX** — Added helpful descriptions to all configuration fields:
  - Provider picker now explains preset selection and when to use Custom
  - API key field shows expected format for each protocol (sk-ant-..., sk-...)
  - Recommended mode toggle explains what it simplifies
  - Temperature, Top P, and Thinking Budget fields now include clear explanations of their purpose and valid ranges
  - Model selection includes helpful labels (e.g., "- Latest, most capable") to distinguish similar models
- **Model description labels** — Each model in the selector now includes a brief description highlighting its key characteristics (speed, capability, cost-effectiveness) to help users choose the right model
- **Inline validation hints** — Thinking Budget field now includes inline text explaining the constraint relationship with Maximum tokens
- **Organized model options schema** — Anthropic model options form now has clear section separators for Response Options, Extended Thinking, Web Capabilities, and Tool Options

### Fixed

- **Test compatibility with Python 3.13** — Updated phantom-python-tester Docker image to Python 3.13-slim for compatibility with pytest-homeassistant-custom-component==0.13.270
- **Test assertion for model labels** — Updated test_flow_get_model_list to check for prefix match instead of exact equality to accommodate new description labels

## 1.2.0-beta.4

Pre-release: Home Assistant 2026.8 dependency compatibility update.

### Changed

- Updated `anthropic` dependency from 0.96.0 to 0.108.0 for Home Assistant 2026.8 compatibility
- Updated `openai` dependency from 2.21.0 to 2.45.0 for Home Assistant 2026.8 compatibility

## 1.2.0-beta.3

Pre-release: bug fixes for streaming, reauthentication, and provider defaults.

### Fixed

- **Usage metrics now included with streaming responses ending in usage-on-content chunks** — streaming responses that end with `usage-on-content` chunks now properly return `ChatCompletion.usage` metadata. Previously, usage was omitted for these responses.
- **Provider get_default_model() override available** — the `Provider` base class now exposes a `get_default_model()` method that custom providers can override to specify their own default instead of using the Anthropic default.
- **Reauthentication preserves entry endpoint** — during reauth, the entry's `protocol` and `base_url` are now preserved and used for validation instead of preset defaults. Retry after failed validation continues using the entry's endpoint; no preset key is introduced.
- **Streaming chunk handling improved** — better handling of streaming responses with usage-on-content chunks for proper token accounting and response completion.

## 1.2.0-beta.2

Pre-release: code-review follow-up to 1.2.0-beta.1.

### Fixed

- **Provider defaults are now authoritative per protocol** — the base entity no longer merges the Anthropic `DEFAULT` for every protocol, nor falls back to a Claude model id on OpenAI entries. Each provider exposes a `defaults()` method (Anthropic → `DEFAULT`, OpenAI → `DEFAULT_OPENAI`), so an OpenAI recommended-mode subentry now correctly gets `gpt-4o-mini` / temperature / top P / reasoning-effort defaults, and an OpenAI entry with an empty `/v1/models` no longer hands the endpoint a Claude id (which would `400`). Removes the last cross-protocol constant coupling from the entity. (Code review items 1 & 2.)

### Changed

- Documented that OpenAI-hosted reasoning models (o-series, gpt-5) are unsupported on this rail — they reject `max_tokens` and non-default temperature. Use chat models (e.g. `gpt-4o-mini`) or compatible/local servers. (Code review item 3.)
- Clarified that the OpenAI stream transformer's `output_tool` parameter is intentionally unused (structured output is native via `response_format`). (Code review item 5.)

## 1.2.0-beta.1

Pre-release: provider-pluggable architecture with OpenAI Chat Completions support. Stable 1.2.0 will follow after testing.

### Added

- **OpenAI Chat Completions protocol** — target any OpenAI-compatible endpoint (`/v1/chat/completions`): OpenAI, OpenRouter, Groq, Together, Ollama, LM Studio, vLLM, llama.cpp, Mistral, and self-hosted servers. (Not OpenAI's Responses API.)
- **Provider-pluggable architecture** behind a new `LLMProvider` interface; the Anthropic path is unchanged (behavior-preserving refactor).
- **Provider preset picker** at setup (with a Custom option). OpenAI entries expose temperature, top P, and reasoning effort.

### Changed

- `openai==2.21.0` added to requirements; repairs and diagnostics routed through the active provider; config entries migrate v1 → v2 (existing entries gain `protocol=anthropic`).

### Fixed

- Deprecated-model repair flow failed to load on Home Assistant 2025.8.1 (`RepairsFlowResult` is not exported); now uses `FlowResult`.

> Note: a `1.1.3` release was referenced in earlier notes but was never published; `1.2.0` follows the shipped `1.1.2`.

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
