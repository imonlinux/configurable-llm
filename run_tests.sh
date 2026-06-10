#!/bin/bash
# Test runner for Configurable LLM integration
# This script installs dependencies and runs tests in the python-tester container

set -e

echo "Installing dependencies..."
pip install -q \
  homeassistant \
  pytest-homeassistant-custom-component \
  anthropic==0.96.0 \
  voluptuous \
  voluptuous-openapi \
  hassil \
  home-assistant-intents

echo "Running tests..."
pytest tests/ -v --tb=short "$@"
