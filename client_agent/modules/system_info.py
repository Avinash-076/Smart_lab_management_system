import getpass
import platform
import socket
import uuid

import psutil


def get_lan_ip() -> str:
    """
    Return the first non-loopback IPv4 address found
    on the computer.

    This does not contact the Internet and therefore
    works correctly in a LAN-only SLMS environment.
    """

    try:
        interfaces = psutil.net_if_addrs()

        for _, addresses in interfaces.items():

            for address in addresses:

                if address.family != socket.AF_INET:
                    continue

                ip_address = address.address

                if not ip_address:
                    continue

                if ip_address.startswith("127."):
                    continue

                return ip_address

    except Exception:
        pass

    return "Unknown"


def get_mac_address() -> str:
    """
    Return the computer MAC address.
    """

    mac = uuid.getnode()

    return ":".join(
        f"{(mac >> shift) & 0xff:02x}"
        for shift in range(40, -8, -8)
    )


def get_system_info() -> dict:
    """
    Collect basic computer and operating-system information.
    """

    return {
        "computer_name": socket.gethostname(),
        "username": getpass.getuser(),
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ip_address": get_lan_ip(),
        "mac_address": get_mac_address(),
    }