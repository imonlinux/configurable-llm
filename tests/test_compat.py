"""Test compatibility layer for newer Home Assistant features.

This module provides mocks for Home Assistant features that don't exist
in the current stable release but are used in the Configurable LLM integration.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
import sys


def setup_test_compatibility() -> None:
    """Set up compatibility shims for testing with current Home Assistant."""
    # Mock ConfigSubentry
    try:
        from homeassistant.config_entries import ConfigSubentry
    except ImportError:
        class MockConfigSubentry:
            """Mock ConfigSubentry for testing."""
            def __init__(self) -> None:
                self.subentry_id = "test_subentry_id"
                self.subentry_type = "conversation"
                self.title = "Test Subentry"
                self.unique_id = "test_unique_id"
                self.data = {}

        # Add ConfigSubentry to HA config_entries module
        import homeassistant.config_entries as ha_ce
        ha_ce.ConfigSubentry = MockConfigSubentry  # type: ignore[attr-defined]

    # Mock ConfigSubentryFlow
    try:
        from homeassistant.config_entries import ConfigSubentryFlow
    except ImportError:
        class MockConfigSubentryFlow:
            """Mock ConfigSubentryFlow for testing."""
            pass
        import homeassistant.config_entries as ha_ce
        ha_ce.ConfigSubentryFlow = MockConfigSubentryFlow  # type: ignore[attr-defined]

    # Mock SubentryFlowResult
    try:
        from homeassistant.config_entries import SubentryFlowResult
    except ImportError:
        SubentryFlowResult = dict  # type: ignore[misc,assignment]
        import homeassistant.config_entries as ha_ce
        ha_ce.SubentryFlowResult = SubentryFlowResult  # type: ignore[attr-defined]

    # Mock AddConfigEntryEntitiesCallback
    try:
        from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    except ImportError:
        AddConfigEntryEntitiesCallback = MagicMock  # type: ignore[misc,assignment]
        import homeassistant.helpers.entity_platform as ha_ep
        ha_ep.AddConfigEntryEntitiesCallback = AddConfigEntryEntitiesCallback  # type: ignore[attr-defined]

    # Mock Platform.AI_TASK
    from homeassistant.const import Platform
    if not hasattr(Platform, "AI_TASK"):
        # Create a fake AI_TASK enum value
        Platform.AI_TASK = "ai_task"  # type: ignore[attr-defined]

    # Mock CONF_PROMPT if it doesn't exist
    import homeassistant.const as ha_const
    if not hasattr(ha_const, "CONF_PROMPT"):
        ha_const.CONF_PROMPT = "prompt"  # type: ignore[attr-defined]

    # Mock ai_task components
    try:
        from homeassistant.components import ai_task
    except ImportError:
        # Create a mock ai_task module
        ai_task = MagicMock()
        ai_task.AITaskEntity = MagicMock
        ai_task.AITaskEntityFeature = SimpleNamespace(
            GENERATE_DATA="generate_data",
            SUPPORT_ATTACHMENTS="support_attachments",
        )
        ai_task.GenDataTask = MagicMock
        ai_task.GenDataTaskResult = MagicMock
        sys.modules["homeassistant.components.ai_task"] = ai_task

    # Mock mimetypes.guess_file_type (removed in Python 3.13)
    import mimetypes
    if not hasattr(mimetypes, "guess_file_type"):
        mimetypes.guess_file_type = mimetypes.guess_type  # type: ignore[attr-defined]


# Auto-setup compatibility when imported
setup_test_compatibility()
