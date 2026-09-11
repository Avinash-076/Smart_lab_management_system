import psutil
from datetime import datetime


def get_hardware_info():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    boot_time = datetime.fromtimestamp(psutil.boot_time())

    return {
        "cpu_usage": psutil.cpu_percent(interval=1),

        "ram_total_gb": round(memory.total / (1024**3), 2),
        "ram_used_gb": round(memory.used / (1024**3), 2),
        "ram_percent": memory.percent,

        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,

        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S")
    }