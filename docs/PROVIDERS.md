# Provider setup

This integration speaks two API contracts, selected by the **API protocol** field at setup:

- **Anthropic** — the Anthropic Messages API (`/v1/messages`): the official Anthropic API, z.ai, and Anthropic-compatible proxies.
- **OpenAI Chat Completions** (`/v1/chat/completions`) — the de-facto standard for opensource/local LLM inference: OpenAI, OpenRouter, Groq, Together, Ollama, LM Studio, vLLM, llama.cpp, Mistral, and self-hosted servers.

Pick a **Provider** preset at setup to fill in the protocol and base URL for you, or choose **Custom** and enter them yourself. The integration's configuration is UI-only — there's nothing to put in `configuration.yaml`.

> This integration **complements** Home Assistant's built-in Anthropic and OpenAI integrations; it does not replace them. If you are using the official Anthropic or OpenAI cloud APIs, the built-in integrations are the better choice. Use this one when you need an Anthropic- or OpenAI-compatible endpoint that the built-ins can't target.

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

## OpenAI-compatible providers

These providers implement the OpenAI Chat Completions API (`/v1/chat/completions`). Select the matching **Provider** preset at setup, or choose **Custom** with the **OpenAI Chat Completions** protocol.

| Provider | Base URL | Notes |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | Core's built-in OpenAI integration is the better choice for the official API. |
| OpenRouter | `https://openrouter.ai/api/v1` | Routes to many models/providers behind one key. |
| Groq | `https://api.groq.com/openai/v1` | Fast inference; check supported model IDs. |
| Together | `https://api.together.xyz/v1` | |
| Mistral | `https://api.mistral.ai/v1` | Mistral's OpenAI-compatible endpoint. |
| Google Gemini (compat) | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini's OpenAI-compatible endpoint. |
| Ollama (local) | `http://localhost:11434/v1` | Set `OLLAMA_ORIGINS` if HA runs on another host. |
| LM Studio (local) | `http://localhost:1234/v1` | Start the local server and load a model first. |
| vLLM (local) | `http://localhost:8000/v1` | Supports `--guided-json` for structured output. |
| llama.cpp server (local) | `http://localhost:8080/v1` | |

**Things to watch for:**

- OpenAI-compatible `/v1/models` endpoints return **no capability information**, so the integration can't auto-detect features. Configure temperature/top P/reasoning effort manually; leave unsupported tool toggles off.
- **Reasoning effort** is model-dependent — only set it above *Default* for reasoning models (e.g. o-series). Some local servers reject the parameter.
- **Attachments** are image-only on this protocol (vision models); PDFs are not supported via Chat Completions.
- **Structured output** uses the `json_schema` response format, supported by OpenAI and by vLLM/Ollama guided decoding. Servers without it will error on AI Task structured output.

## Self-hosted / local LLM servers

Most local servers (Ollama, LM Studio, vLLM, llama.cpp) speak the **OpenAI Chat Completions** protocol — see the table above. This section covers servers that instead expose an **Anthropic-compatible** endpoint (llama.cpp's Claude-compat mode, vLLM with the Claude adapter, certain proxies).

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
- Turn off **Recommended model settings** to expose model selection and the protocol-specific advanced options (prompt caching / thinking for Anthropic; temperature / top P / reasoning effort for OpenAI Chat Completions) plus tool toggles.

If the model list call fails during setup with an authentication error, the API key is wrong. If it fails with a connection error, the base URL is wrong or the provider is unreachable.
