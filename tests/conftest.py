"""Fixtures for SIP Assistant tests."""

from __future__ import annotations

from collections.abc import Generator
import socket
from typing import Any

from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sip_assistant.config_flow import default_options
from custom_components.sip_assistant.const import (
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    DOMAIN,
    SECTION_NETWORK,
    Engine,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration."""


def free_udp_port() -> int:
    """Return a currently unused UDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def sip_port(socket_enabled: None) -> int:
    """Return a free port for the SIP server."""
    return free_udp_port()


@pytest.fixture
def entry_data(sip_port: int) -> dict[str, Any]:
    """Return config entry data."""
    return {
        CONF_SIP_PORT: sip_port,
        CONF_SIP_USER: "homeassistant",
        CONF_SIP_PASSWORD: "",
        CONF_API_KEY: "",
    }


@pytest.fixture
def mock_config_entry(hass: HomeAssistant, entry_data: dict[str, Any]) -> MockConfigEntry:
    """Return a config entry using a free port and an RTP range for tests."""
    options = default_options(hass, Engine.LIVE)
    options[SECTION_NETWORK] |= {"rtp_port_start": 43000, "rtp_port_end": 43100}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SIP Assistant",
        data=entry_data,
        options=options,
        version=1,
        minor_version=1,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_port_check() -> Generator[None]:
    """Pretend every port is free."""
    from unittest.mock import patch

    with patch("custom_components.sip_assistant.config_flow._port_available", return_value=True):
        yield
