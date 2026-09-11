import socket
import uuid
import psutil


def get_network_info():
    hostname = socket.gethostname()

    # Get the real LAN IP
    ip_address = "Unknown"

    # try:
    #     for interface, addresses in psutil.net_if_addrs().items():
    #         for addr in addresses:
    #             if addr.family == socket.AF_INET:
    #                 if not addr.address.startswith("127."):
    #                     ip_address = addr.address
    #                     break
    # except Exception:
    #     pass

    found = False
    for interface, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == socket.AF_INET:
                if not addr.address.startswith("127."):
                    ip_address = addr.address
                    found = True
                    break
        if found:
            break


    mac = ":".join(
        f"{(uuid.getnode() >> ele) & 0xff:02x}"
        for ele in range(40, -8, -8)
    )

    stats = psutil.net_io_counters()

    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "mac_address": mac,
        "bytes_sent": stats.bytes_sent,
        "bytes_received": stats.bytes_recv
    }