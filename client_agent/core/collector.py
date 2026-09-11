from config import (
    ENABLE_SYSTEM_INFO,
    ENABLE_HARDWARE_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_PROCESS_INFO,
    ENABLE_NETWORK_INFO,
)

from modules.system_info import get_system_info
from modules.hardware import get_hardware_info
from modules.software import get_installed_software
from modules.processes import get_running_processes
from modules.network import get_network_info

from core.health import safe_run


def collect_all_data():

    data = {}

    if ENABLE_SYSTEM_INFO:
        data["system"] = safe_run(
            "System Information",
            get_system_info
        )

    if ENABLE_HARDWARE_INFO:
        data["hardware"] = safe_run(
            "Hardware Information",
            get_hardware_info
        )

    if ENABLE_SOFTWARE_INFO:
        data["software"] = safe_run(
            "Installed Software",
            get_installed_software
        )

    if ENABLE_PROCESS_INFO:
        data["processes"] = safe_run(
            "Running Processes",
            get_running_processes
        )

    if ENABLE_NETWORK_INFO:
        data["network"] = safe_run(
            "Network Information",
            get_network_info
        )

    return data