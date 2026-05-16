# Configurable LLM for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Home Assistant](https://img.shields.io/badge/Home_Assistant-2024.1.0%2B-blue.svg)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Pending-orange.svg)](https://hacs.xyz/)

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

### Option 1: Via HACS (Recommended)

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=imonlinux&repository=configurable-llm&category=integration)

1. **Install HACS** if you haven't already:
   ```bash
   wget -O - https://get.hacs.xyz | bash -
   ```

2. **Add this repository to HACS:**
   - Open HACS in Home Assistant
   - Go to Integrations → Click the three dots (⋮) → "Custom repositories"
   - Add: `https://github.com/imonlinux/configurable-llm`
   - Category: "Integration"

3. **Install the integration:**
   - In HACS, search for "Configurable LLM"
   - Click "Download" → "Install"
   - Restart Home Assistant when prompted

4. **Configure the integration:**
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Configurable LLM"
   - Configure with your API provider details (see Configuration section)

### Option 2: Manual Installation

1. **Download the component:**
   ```bash
   git clone https://github.com/imonlinux/configurable-llm.git
   cd configurable-llm
   ```

2. **Copy to your Home Assistant configuration:**
   ```bash
   cp -r custom_components/configurable_llm /path/to/homeassistant/custom_components/
   ```

3. **Restart Home Assistant**

4. **Add the integration:**
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Configurable LLM"
   - Configure with your API provider details

## ⚙️ Configuration

### Required Settings
- **API Key**: Your API key for the LLM service

### Optional Settings
- **Base URL**: The API endpoint URL
  - Default: `https://api.anthropic.com` (official Anthropic API)
  - For z.ai: `https://api.z.ai/v1/` (note trailing slash)
  - For local servers: `http://localhost:8080/v1/`
  - **Important**: URL should end with `/` for most providers
  - For custom providers: Check their documentation

## 🔧 Usage Examples

### Example 1: Using z.ai
```
API Key: sk-your-zai-key
Base URL: https://api.z.ai/v1/
```
**Note**: Make sure to include the trailing slash `/` at the end.

### Example 2: Official Anthropic API
```
API Key: sk-ant-your-key
Base URL: (leave blank for default)
```

### Example 3: Local LLM Server
```
API Key: any-key
Base URL: http://localhost:8080/v1/
```
**Note**: Include trailing slash for local servers as well.

## 🔄 Updating

### Via HACS
- Open HACS → Integrations
- Click "Configurable LLM"
- Click "Update" if a new version is available
- Restart Home Assistant when prompted

### Manual Update
1. Navigate to your configurable-llm directory and pull latest changes:
   ```bash
   cd /path/to/configurable-llm
   git pull
   ```
2. Copy the updated files to your Home Assistant:
   ```bash
   cp -r custom_components/configurable_llm /path/to/homeassistant/custom_components/
   ```
3. Restart Home Assistant

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

## 🗑️ Uninstalling

### Via HACS
1. Go to Settings → Devices & Services
2. Find "Configurable LLM Integration" → Click the three dots (⋮) → "Delete"
3. Open HACS → Integrations → "Configurable LLM Integration"
4. Click the three dots (⋮) → "Uninstall"
5. Restart Home Assistant

### Manual Removal
1. Go to Settings → Devices & Services
2. Find "Configurable LLM Integration" → Click the three dots (⋮) → "Delete"
3. Delete the component folder:
   ```bash
   rm -rf /path/to/homeassistant/custom_components/configurable_llm
   ```
4. Restart Home Assistant

## 🔍 Troubleshooting

### URL Format Issues
**Common base URL problems:**
- **Missing trailing slash**: `https://api.z.ai/v1` ❌ → `https://api.z.ai/v1/` ✅
- **Wrong path**: Check provider documentation for correct API path
- **HTML 404 errors**: Usually means wrong URL format or missing path
- **Case sensitivity**: URLs are case-sensitive

**Testing your base URL:**
```bash
# Test if endpoint is accessible
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://your-base-url/v1/messages

# Should return JSON response, not HTML
```

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

**Repository**: https://github.com/imonlinux/configurable-llm
**Issues**: https://github.com/imonlinux/configurable-llm/issues

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

Based on the [official Home Assistant Anthropic integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/anthropic).

---

**Component Name**: Configurable LLM
**Domain**: `configurable_llm`
**Version**: 1.0.0
**Status**: ✅ Ready for installation and testing
