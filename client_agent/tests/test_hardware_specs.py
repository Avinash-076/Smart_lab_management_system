from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from modules.hardware import (
    _parse_wmi_date,
    _format_boot_time,
    get_detailed_hardware_specs,
)
from server.sender import send_hardware_specs


def test_parse_wmi_date():
    """Verify parsing of various WMI / CIM date formats."""
    # /Date(ms)/ format
    assert _parse_wmi_date("/Date(1738673068000)/", date_only=True) == "04-02-2025"
    # YYYYMMDD format
    assert _parse_wmi_date("20240210123000.000000+000", date_only=True) == "10-02-2024"
    # None or empty
    assert _parse_wmi_date(None) is None
    assert _parse_wmi_date("") is None


def test_format_boot_time():
    """Verify relative boot time formatting."""
    now = datetime.now()
    today_boot = now.replace(hour=6, minute=15)
    formatted = _format_boot_time(today_boot)
    assert formatted.startswith("Today, 06:15")


def test_get_detailed_hardware_specs_keys():
    """Verify get_detailed_hardware_specs returns all required hardware specification keys."""
    specs = get_detailed_hardware_specs()
    assert isinstance(specs, dict)

    required_keys = [
        "manufacturer",
        "model",
        "serial_number",
        "system_type",
        "bios_version",
        "bios_date",
        "processor_name",
        "processor_cores",
        "processor_threads",
        "processor_base_speed",
        "processor_max_speed",
        "ram_total_gb",
        "ram_usable_gb",
        "ram_type",
        "ram_speed",
        "ram_slots_used",
        "ram_slots_total",
        "storage_drives_count",
        "storage_total_gb",
        "storage_type",
        "storage_health",
        "gpu_name",
        "gpu_memory_mb",
        "gpu_driver_version",
        "subnet_mask",
        "default_gateway",
        "dns_servers",
        "connection_type",
        "motherboard_manufacturer",
        "motherboard_model",
        "motherboard_chipset",
        "motherboard_serial",
        "os_install_date",
        "last_boot_time",
        "power_plan",
        "agent_version",
    ]

    for key in required_keys:
        assert key in specs, f"Missing required key: {key}"


@patch("server.sender.get_api_base_url", return_value="https://test.slms.local")
@patch("server.sender.create_secure_session")
def test_send_hardware_specs(mock_create_session, mock_get_url):
    """Verify send_hardware_specs sends POST request to /api/clients/hardware."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "computer_id": 42}
    mock_session.post.return_value = mock_response
    mock_create_session.return_value = mock_session

    sample_specs = {
        "processor_name": "Intel Core i5-10400",
        "ram_total_gb": 16.0,
    }

    result = send_hardware_specs(sample_specs, "test_token_123")

    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert "/api/clients/hardware" in call_args[0][0]
    assert call_args[1]["json"] == sample_specs
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_token_123"
    assert result == {"id": 1, "computer_id": 42}
