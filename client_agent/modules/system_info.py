import getpass
import platform
import socket
import uuid


def get_lan_ip():

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:

        sock.connect(
            ("8.8.8.8", 80)
        )

        return sock.getsockname()[0]

    except Exception:

        return "Unknown"

    finally:

        sock.close()


def get_mac_address():

    return ":".join(
        f"{(uuid.getnode() >> ele) & 0xff:02x}"
        for ele in range(40, -8, -8)
    )


def get_system_info():

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