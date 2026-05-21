# Provider setup

This document covers the API base URLs and notes for various Anthropic-compatible providers. The integration's configuration is UI-only — there's nothing to put in `configuration.yaml`.

## Official Anthropic API

| Field | Value |
|---|---|
| API base URL | `https://api.anthropic.com` (default — leave as-is) |
| API key format | `sk-ant-...` |

Use Home Assistant's built-in Anthropic integration instead unless you have a specific reason to use this one (e.g., running it alongside another configured Anthropic-compatible provider).

## Anthropic-compatible providers

The integration works with any service that implements Anthropic's `/v1/messages` API. The base URL is whatever the provider documents — usually a path under their domain.

A few quick examples:

| Provider | Base URL pattern |
|---|---|
| Generic Anthropic-compatible | `https://provider.example.com/api/anthropic` or `https://provider.example.com/v1/` |
| API gateway / proxy | Whatever URL your gateway exposes |

**Things to watch for:**

- The trailing slash matters for some providers. If you get a 404 or "Invalid API endpoint" error during setup, try toggling it.
- Some providers require an `anthropic-version` header. The Anthropic Python SDK sets a recent default; if your provider rejects requests with an unsupported version, that needs to be fixed on the provider side.
- Provider tool support varies. Some support web search and tool use; many don't. Leave those toggles off in the conversation/AI task subentry until you've confirmed support.

### Example: z.ai

z.ai is one provider known to work with this integration. Tested setup:

| Field | Value |
|---|---|
| API base URL | `https://api.z.ai/api/anthropic` |
| API key format | provider-issued |

Other providers may differ in URL structure — consult their docs.

## Self-hosted / local LLM servers

Local server software that exposes an Anthropic-compatible endpoint (llama.cpp's Claude-compat mode, certain LM Studio configurations, vLLM with Claude adapter, etc.) can be used.

| Field | Value |
|---|---|
| API base URL | `http://localhost:8080/v1/` (or whatever your server uses) |
| API key | any non-empty string if the server doesn't require auth |

**Practical notes:**

- The trailing slash is usually required for local servers.
- If the server doesn't implement `/v1/models`, the model dropdown will be empty during configuration. Type the model ID into the field directly — `custom_value` is enabled.
- Most local servers don't implement the more advanced tool features (web search, web fetch, code execution, structured outputs). Leave those toggles off.
- Use the official IP address or hostname of the server, not `localhost`, unless Home Assistant is running on the same machine as the LLM server.

## After setup

The integration tries to fetch the model list from `/v1/models` once during the setup form's submit. If that call succeeds, the integration is configured and two default subentries (one conversation agent, one AI task) are created.

Each subentry can be reconfigured later from **Settings → Devices & Services → Configurable LLM**. From there:

- Click on the subentry's three-dot menu to **Reconfigure**
- Turn off **Recommended model settings** to expose model selection, prompt caching, thinking budget, tool toggles, etc.

If the model list call fails during setup with an authentication error, the API key is wrong. If it fails with a connection error, the base URL is wrong or the provider is unreachable.
