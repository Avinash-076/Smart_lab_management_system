import socket
import platform
import uuid
import getpass


def get_system_info():
    info = {
        "computer_name": socket.gethostname(),
        "username": getpass.getuser(),
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": ":".join(
            f"{(uuid.getnode() >> ele) & 0xff:02x}"
            for ele in range(40, -8, -8)
        )
    }

    return info