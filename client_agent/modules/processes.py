import psutil
from datetime import datetime


def get_running_processes():

    processes = []
    seen = set()

    # Prime CPU measurement
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(None)
        except Exception:
            pass

    for proc in psutil.process_iter([
        "pid",
        "name",
        "username",
        "status",
        "create_time"
    ]):

        try:

            name = proc.info["name"]

            if not name:
                continue

            if name in seen:
                continue

            seen.add(name)

            try:
                start_time = datetime.fromtimestamp(
                    proc.info["create_time"]
                ).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                start_time = "Unknown"

            process = {
                "pid": proc.info["pid"],
                "name": name,
                "user": proc.info["username"],
                "cpu_percent": proc.cpu_percent(interval=None),
                "memory_percent": round(proc.memory_percent(), 2),
                "status": proc.info["status"],
                "start_time": start_time
            }

            processes.append(process)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue

    processes.sort(
        key=lambda x: x["cpu_percent"],
        reverse=True
    )

    return processes