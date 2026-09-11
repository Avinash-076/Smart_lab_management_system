import psutil
from datetime import datetime


def get_running_processes():
    """
    Return information about currently running processes.

    Each process contains:
        - pid
        - process_name
        - executable_path
        - start_time
    """

    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "exe", "create_time"]
    ):
        try:
            process_name = process.info.get("name")
            executable_path = process.info.get("exe")
            create_time = process.info.get("create_time")

            if not process_name:
                continue

            if not create_time:
                continue

            process_info = {
                "pid": process.info["pid"],
                "process_name": process_name,
                "executable_path": executable_path,
                "start_time": datetime.fromtimestamp(create_time),
            }

            processes.append(process_info)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            OSError,
        ):
            continue

    return processes


if __name__ == "__main__":

    running_processes = get_running_processes()

    for process in running_processes:

        print(
            f"PID: {process['pid']} | "
            f"Name: {process['process_name']} | "
            f"Path: {process['executable_path']} | "
            f"Start: {process['start_time']}"
        )