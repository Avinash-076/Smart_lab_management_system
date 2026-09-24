from config import (
    ENABLE_HARDWARE_INFO,
    ENABLE_NETWORK_INFO,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_SYSTEM_INFO,
    ENABLE_USAGE_INFO,
)

from core.health import safe_run

from modules.hardware import get_hardware_info
from modules.network import get_network_info
from modules.processes import get_running_processes
from modules.software import get_installed_software
from modules.system_info import get_system_info
from modules.usage import collect_usage_sessions


def collect_all_data():

    data = {}

    # ------------------------------------------
    # System Information
    # ------------------------------------------

    if ENABLE_SYSTEM_INFO:

        data["system"] = safe_run(
            "System Information",
            get_system_info
        )

    # ------------------------------------------
    # Hardware Information
    # ------------------------------------------

    if ENABLE_HARDWARE_INFO:

        data["hardware"] = safe_run(
            "Hardware Information",
            get_hardware_info
        )

    # ------------------------------------------
    # Software Inventory
    # ------------------------------------------

    if ENABLE_SOFTWARE_INFO:

        data["software"] = safe_run(
            "Installed Software",
            get_installed_software
        )

    # ------------------------------------------
    # Process Monitoring
    # ------------------------------------------

    if ENABLE_PROCESS_INFO:

        data["processes"] = safe_run(
            "Running Processes",
            get_running_processes
        )

    # ------------------------------------------
    # Usage Tracking
    # ------------------------------------------

    if ENABLE_USAGE_INFO:

        data["usage"] = safe_run(
            "Application Usage",
            collect_usage_sessions
        )

    # ------------------------------------------
    # Network Information
    # ------------------------------------------

    if ENABLE_NETWORK_INFO:

        data["network"] = safe_run(
            "Network Information",
            get_network_info
        )

    return data