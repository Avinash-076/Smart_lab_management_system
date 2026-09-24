import psutil
from datetime import datetime, timezone


def get_running_processes():
    processes = []

    for process in psutil.process_iter(
        [
            "pid",
            "name",
            "username",
            "cpu_percent",
            "memory_percent",
            "status",
            "create_time",
        ]
    ):
        try:
            info = process.info

            pid = info.get("pid")
            name = info.get("name")

            if pid is None or not name:
                continue

            username = info.get("username")

            cpu_percent = info.get("cpu_percent") or 0
            memory_percent = info.get("memory_percent") or 0

            status = info.get("status")

            create_time = info.get("create_time")

            start_time = None

            if create_time:
                start_time = datetime.fromtimestamp(
                    create_time,
                    tz=timezone.utc,
                ).isoformat()

            processes.append(
                {
                    "pid": pid,
                    "name": name,
                    "user": username,
                    "cpu_percent": max(
                        0,
                        float(cpu_percent),
                    ),
                    "memory_percent": max(
                        0,
                        float(memory_percent),
                    ),
                    "status": status,
                    "start_time": start_time,
                }
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

        except Exception:
            continue

    processes.sort(
        key=lambda item: (
            item["cpu_percent"],
            item["memory_percent"],
        ),
        reverse=True,
    )

    return processes