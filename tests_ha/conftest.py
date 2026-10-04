"""Tests running inside a real Home Assistant (pytest-homeassistant-custom-component)."""

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components/."""
    yield


@pytest.fixture(autouse=True)
def without_web_server(hass):
    """Skip what needs the web server and the frontend package.

    async_setup only serves the cards and the photos; the flows, entities and
    notifications under test do not depend on it.
    """
    hass.config.components.update({"frontend", "http", "file_upload"})
    with patch("custom_components.plant_manager.async_setup", return_value=True):
        yield
