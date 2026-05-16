# Configuration Examples for Configurable LLM Integration

This document provides configuration examples for various LLM providers and use cases.

## 🌟 Popular Provider Configurations

### z.ai Configuration

#### Basic Setup
```yaml
# Via UI: Settings → Devices & Services → Add Integration → Configurable LLM
# API Key: your-zai-api-key
# Base URL: https://api.z.ai/v1
```

#### Advanced Configuration
```yaml
# configuration.yaml
conversation:
  custom_llm:
    model: "claude-3-5-sonnet-20241022"
    max_tokens: 3000
    temperature: 0.7
```

### Local LLM Server

#### Example with Local API Server
```yaml
# Via UI: Settings → Devices & Services → Add Integration → Configurable LLM
# API Key: any-string-or-real-key
# Base URL: http://localhost:8080/v1
```

#### Docker Setup
```bash
# Example: Running a local API server with Anthropic-compatible endpoints
docker run -p 8080:8080 your-local-llm-server
```

### Official Anthropic API (Default)

#### Standard Setup
```yaml
# Via UI: Settings → Devices & Services → Add Integration → Configurable LLM
# API Key: sk-ant-your-api-key
# Base URL: https://api.anthropic.com (or leave blank)
```

## 🏢 Alternative Providers

### Generic Anthropic-Compatible API
```yaml
# Via UI configuration
# API Key: your-provider-api-key
# Base URL: https://your-provider.com/api/v1
```

### Custom Proxy/Gateway
```yaml
# Via UI configuration
# API Key: your-gateway-key
# Base URL: https://your-gateway.com/llm-proxy
```

## 🎯 Model Selection Examples

### Different Model Configurations
```yaml
# conversation.yaml or via UI
conversation:
  - name: "Fast Responses"
    model: "claude-haiku-4-5"
    max_tokens: 1000

  - name: "Balanced Performance"
    model: "claude-3-5-sonnet-20241022"
    max_tokens: 3000

  - name: "Advanced Reasoning"
    model: "claude-3-5-opus-20241022"
    max_tokens: 8000
```

## 🧪 Testing Your Configuration

### Verify Connection
```bash
# Test your API endpoint with curl
curl -X POST https://your-base-url/v1/messages \
  -H "x-api-key: your-api-key" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Check Home Assistant Logs
```bash
# View logs for connection issues
tail -f home-assistant.log | grep configurable_llm
```

## 📊 Common Base URL Patterns

| Provider | Base URL Pattern | Notes |
|----------|------------------|-------|
| Anthropic Official | `https://api.anthropic.com` | Default |
| z.ai | `https://api.z.ai/v1` | Verify in z.ai docs |
| Local Server | `http://localhost:8080/v1` | Depends on your setup |
| Custom Gateway | `https://your-gateway.com/api` | Your custom endpoint |
| Development Server | `http://dev-server:3000/v1` | Local development |

## 🏠 Home Assistant Integration

### Example Automation
```yaml
# automations.yaml
automation:
  - alias: "Ask LLM about temperature"
    trigger:
      - platform: state
        entity_id: sensor.temperature
    action:
      - service: conversation.process
        target:
          entity_id: conversation.configurable_llm
        data:
          text: "The temperature is {{ states('sensor.temperature') }}. Is this normal?"
```

### Voice Assistant Integration
```yaml
# Configure voice assistant to use your custom LLM
# Via UI: Settings → Voice Assistants → Your Assistant → Conversation Agent
# Select: "LLM conversation"
```

### Script Integration
```yaml
# scripts.yaml
ask_llm_about_energy:
  alias: "Ask LLM about energy usage"
  sequence:
    - service: conversation.process
      target:
        entity_id: conversation.configurable_llm
      data:
        text: "Current energy usage is {{ states('sensor.energy_today') }} kWh. Is this efficient?"
```

## 🔧 Advanced Configuration

### Custom Prompts
```yaml
# Via UI: Settings → Devices & Services → Configurable LLM → Configure
# Or in conversation.yaml
conversation:
  custom_llm:
    prompt: >-
      You are a helpful home automation assistant.
      You have access to Home Assistant devices and can help control the smart home.
      Always consider the context of time, occupancy, and user preferences.
```

### Model-Specific Settings
```yaml
conversation:
  haiku_fast:
    model: "claude-haiku-4-5"
    max_tokens: 500
    temperature: 0.5

  sonnet_balanced:
    model: "claude-3-5-sonnet-20241022"
    max_tokens: 2000
    temperature: 0.7

  opus_advanced:
    model: "claude-3-5-opus-20241022"
    max_tokens: 4000
    temperature: 0.8
```

## 🚨 Troubleshooting Examples

### Fix Connection Timeout
```yaml
# Via UI: Settings → Devices & Services → Configurable LLM → Configure
# Increase timeout in advanced settings if available
# Or configure your API server to have longer timeouts
```

### Handle Rate Limits
```yaml
# Some providers have different rate limits
# Configure appropriate delays in your automations
automation:
  - alias: "Ask LLM with delay"
    trigger:
      - platform: state
        entity_id: sensor.something
    action:
      - delay: "00:00:02"  # 2 second delay
      - service: conversation.process
        target:
          entity_id: conversation.configurable_llm
        data:
          text: "{{ trigger.to_state.state }}"
```

### Debug Mode
```yaml
# Enable debug logging in configuration.yaml
logger:
  default: info
  logs:
    custom_components.configurable_llm: debug
```

## 🌐 Multi-Provider Setup

### Provider Switching
```yaml
# Configure multiple integrations for different providers
# Via UI: Add multiple Configurable LLM integrations

# Integration 1: z.ai (cost-effective)
# Integration 2: Anthropic (official)
# Integration 3: Local (offline)

# Use different conversation entities for different purposes
conversation:
  zai_primary:
    model: "claude-3-5-sonnet-20241022"

  anthropic_backup:
    model: "claude-3-5-sonnet-20241022"

  local_offline:
    model: "local-model-name"
```

## 📝 Notes on API Compatibility

### Feature Support
- **Not all providers support every feature**
- Check provider documentation for:
  - Available models
  - Rate limits
  - Supported parameters
  - Response format compatibility

### Authentication Methods
- Most providers use API key authentication
- Some may require additional headers
- Custom authentication may require component modifications

### Model Naming
- Model names may vary between providers
- Check provider documentation for exact model names
- Some providers may use aliases

## 🔍 Verification Checklist

Before using in production:
- [ ] Test connection with curl
- [ ] Verify model list loads correctly
- [ ] Test basic conversation
- [ ] Check rate limits
- [ ] Verify cost structure
- [ ] Test with automations
- [ ] Configure error handling
- [ ] Set up monitoring/logging

Always test your configuration thoroughly before deploying to production.
