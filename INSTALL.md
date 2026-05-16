# Installation Guide for Configurable LLM Integration

## 🚀 Quick Installation

### Option 1: Manual Installation

1. **Download the component:**
   ```bash
   git clone https://github.com/yourusername/configurable-llm-integration.git
   cd configurable-llm-integration
   ```

2. **Copy to Home Assistant:**
   ```bash
   # Create the custom_components directory if it doesn't exist
   mkdir -p /path/to/homeassistant/custom_components/

   # Copy the component
   cp -r custom_components/configurable_llm /path/to/homeassistant/custom_components/
   ```

3. **Restart Home Assistant:**
   - Via UI: Settings → System → System → Restart
   - Via terminal: `ha restart` or `systemctl restart home-assistant`

### Option 2: HACS Installation (Future)

If this component is added to HACS:
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click "Explore & Add Integrations"
4. Search for "Configurable LLM"
5. Click "Download"
6. Restart Home Assistant

## ⚙️ Post-Installation Setup

### 1. Add the Integration

1. Go to **Settings → Devices & Services**
2. Click **"Add Integration"**
3. Search for **"Configurable LLM"**
4. Click on it

### 2. Configure Your Provider

You'll need to provide:

**Required:**
- **API Key**: Your API key for the LLM service

**Optional:**
- **Base URL**: The API endpoint URL
  - Leave blank for official Anthropic API
  - For z.ai: `https://api.z.ai/v1`
  - For local servers: `http://localhost:8080/v1`
  - For other services: Check their documentation

### 3. Test the Connection

After configuration:
1. The integration will attempt to fetch available models
2. If successful, you'll see "Configurable LLM" in your integrations
3. You can then configure conversations and AI tasks

## 🌐 Popular Provider Configurations

### z.ai
```
API Key: sk-your-zai-key
Base URL: https://api.z.ai/v1
```

### Official Anthropic API
```
API Key: sk-ant-your-key
Base URL: (leave blank)
```

### Local LLM Server
```
API Key: any-key-or-real-key
Base URL: http://localhost:8080/v1
```

### Custom Provider
```
API Key: your-provider-key
Base URL: https://your-provider.com/api/v1
```

## ✅ Verifying Installation

### Check Logs
```bash
# Home Assistant logs should show:
# INFO: Setup of domain configurable_llm took X.XX seconds.
```

### Check Integration List
- Go to **Settings → Devices & Services**
- Look for **"Configurable LLM"** in the list
- Status should show as **"Connected"**

### Test Conversation
1. Go to **Developer Tools → YAML**
2. Test the conversation agent:
   ```yaml
   service: conversation.process
   target:
     entity_id: conversation.configurable_llm
   data:
     text: "Hello, can you hear me?"
   ```

## 🔧 Troubleshooting

### Component Not Showing Up
- Ensure the folder is named exactly `configurable_llm`
- Check that all files are in the correct location
- Restart Home Assistant completely

### Connection Errors
- Verify the base URL is accessible from your network
- Check that the API key is correct
- Look at Home Assistant logs for specific error messages

### Model List Not Loading
- Some alternative APIs may not support the models list endpoint
- You can still use the integration by manually specifying models

## 🗑️ Uninstallation

To remove the component:

1. **Remove the integration:**
   - Go to **Settings → Devices & Services**
   - Find **"Configurable LLM"**
   - Click the menu (⋮)
   - Select **"Delete"**

2. **Remove the files:**
   ```bash
   rm -rf /path/to/homeassistant/custom_components/configurable_llm
   ```

3. **Restart Home Assistant**

## 🎯 Next Steps

After installation:
- Configure conversation agents (see EXAMPLES.md)
- Set up AI tasks for automation
- Integrate with voice assistants
- Explore advanced features in the configuration UI

## 📚 Additional Resources

- **[Configuration Examples](EXAMPLES.md)**: Detailed setup examples
- **[Component Summary](COMPONENT_SUMMARY.md)**: Technical overview
- **[Main README](README.md)**: Full feature documentation

## 💡 Tips

- **Start with Default**: Use official Anthropic API first to ensure everything works
- **Test Thoroughly**: Try each provider before using in production
- **Check Logs**: Enable debug logging for troubleshooting
- **Backup Config**: Save your working configurations before making changes

## 🆘 Support

For issues specific to this component:
- Check the GitHub repository
- Review the troubleshooting section
- Enable debug logging in Home Assistant
- Check provider documentation for API-specific issues

For provider-specific issues (z.ai, etc.):
- Consult their documentation
- Verify API compatibility with Anthropic's format
- Check their status pages
