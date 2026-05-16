# Configurable LLM Integration for Home Assistant

A custom Home Assistant component that provides configurable LLM (Large Language Model) integration with support for multiple API providers. Based on the official Anthropic integration, this component adds the ability to use alternative providers like z.ai or any Anthropic-compatible API.

## 🎯 Key Features

- **🔧 Configurable API Base URL**: Connect to any Anthropic-compatible API endpoint
- **🌐 Multiple Provider Support**: Works with official Anthropic API, z.ai, local servers, and more
- **💬 Full Conversation Support**: Complete conversation agent functionality
- **🤖 AI Task Automation**: Build intelligent automations with LLM assistance
- **🎯 Feature Parity**: Maintains all functionality from the official integration

## 🚀 Use Cases

### Alternative LLM Providers
- **z.ai**: Cost-effective alternative with compatible API
- **Local LLM Servers**: Self-hosted models for privacy and offline capability
- **API Gateways**: Custom routing and monitoring
- **Development**: Test with mock servers before production

### Flexible Deployment
- **Privacy-Sensitive**: Keep data on-premise with local servers
- **Cost Optimization**: Choose providers based on pricing
- **Redundancy**: Switch between providers seamlessly
- **Regional**: Use providers closer to your location

## 📦 Installation

### Option 1: Manual Installation

1. **Copy the component to Home Assistant:**
   ```bash
   cp -r ~/repos/configurable-llm-integration/custom_components/configurable_llm /path/to/homeassistant/custom_components/
   ```

2. **Restart Home Assistant**

3. **Add the integration:**
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Configurable LLM"
   - Configure with your API provider details

### Option 2: HACS Installation
If added to HACS in the future, install through the HACS interface.

## ⚙️ Configuration

### Required Settings
- **API Key**: Your API key for the LLM service

### Optional Settings
- **Base URL**: The API endpoint URL
  - Default: `https://api.anthropic.com` (official Anthropic API)
  - For z.ai: `https://api.z.ai/v1`
  - For local servers: `http://localhost:8080/v1`
  - For custom providers: Check their documentation

## 🔧 Usage Examples

### Example 1: Using z.ai
```
API Key: sk-your-zai-key
Base URL: https://api.z.ai/v1
```

### Example 2: Official Anthropic API
```
API Key: sk-ant-your-key
Base URL: (leave blank for default)
```

### Example 3: Local LLM Server
```
API Key: any-key
Base URL: http://localhost:8080/v1
```

## 📚 Features

### Conversation Agents
- Multiple conversation configurations
- Custom prompts and instructions
- Model selection (Claude Haiku, Sonnet, Opus)
- Token limit control
- Temperature and other parameters

### AI Tasks
- Automated home intelligence
- Trigger-based AI responses
- HASS API integration
- Custom action execution

### Advanced Options
- Prompt caching for performance
- Thinking budget for complex reasoning
- Tool use and web search
- Code execution capabilities

## 🛠️ Technical Details

### Component Structure
```
configurable_llm/
├── __init__.py           # Main integration setup
├── const.py              # Constants and defaults
├── config_flow.py        # Configuration UI flow
├── coordinator.py        # API client with base URL support
├── manifest.json         # Component metadata
├── strings.json          # UI strings
└── services.yaml         # Service definitions
```

### Key Implementation
- Uses the official Anthropic Python SDK
- Configurable base URL via `base_url` parameter
- Maintains compatibility with Anthropic's API specification
- Supports all standard conversation and AI task features

## 🔍 Troubleshooting

### Connection Issues
- Verify base URL is accessible from your network
- Check API key validity
- Review Home Assistant logs for specific errors
- Test endpoint with curl/Postman

### Model List Not Loading
- Some providers don't support the models list endpoint
- You can still manually specify models in conversations
- Check provider documentation for available models

### Authentication Errors
- Double-check API key
- Verify provider authentication method
- Check if API key has required permissions

## 📖 Documentation

- **[Installation Guide](INSTALL.md)**: Detailed setup instructions
- **[Configuration Examples](EXAMPLES.md)**: Various provider configurations
- **[Component Summary](COMPONENT_SUMMARY.md)**: Technical overview

## ⚠️ Compatibility Notes

- **API Compatibility**: Works with Anthropic-compatible APIs
- **Feature Parity**: Not all providers support every feature
- **Model Availability**: Varies by provider
- **Rate Limits**: Different limits per provider

## 🤝 Contributing

This component is based on the official Home Assistant Anthropic integration.
Contributions should maintain compatibility with the original architecture.

## 📄 License

This component follows the same license as the official Home Assistant integration.

## 🙏 Credits

Based on the [official Home Assistant Anthropic integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/anthropic).

---

**Component Name**: Configurable LLM Integration
**Domain**: `configurable_llm`
**Version**: 1.0.0
**Status**: ✅ Ready for installation and testing
