import os
from datetime import datetime

import psutil


def get_hardware_info():

    memory = psutil.virtual_memory()

    system_drive = os.environ.get(
        "SystemDrive",
        "C:"
    )

    disk = psutil.disk_usage(
        system_drive + "\\"
    )

    boot_time = datetime.fromtimestamp(
        psutil.boot_time()
    )

    return {
        "cpu_usage": psutil.cpu_percent(
            interval=1
        ),

        "cpu_count": psutil.cpu_count(
            logical=True
        ),

        "ram_total_gb": round(
            memory.total / (1024 ** 3),
            2
        ),

        "ram_used_gb": round(
            memory.used / (1024 ** 3),
            2
        ),

        "ram_percent": memory.percent,

        "disk_total_gb": round(
            disk.total / (1024 ** 3),
            2
        ),

        "disk_used_gb": round(
            disk.used / (1024 ** 3),
            2
        ),

        "disk_percent": disk.percent,

        "boot_time": boot_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }