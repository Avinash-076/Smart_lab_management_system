import ctypes
import subprocess

from core.logger import logger


def handle_message(payload):
    try:
        message = payload or "Message from administrator"

        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            "SLMS Notice",
            0x40
        )

        return True, "Message displayed"

    except Exception as e:
        logger.exception(
            "Failed to display message"
        )

        return False, str(e)


def handle_lock(payload):
    try:
        ctypes.windll.user32.LockWorkStation()

        return True, "Workstation locked"

    except Exception as e:
        logger.exception(
            "Failed to lock workstation"
        )

        return False, str(e)


def handle_restart(payload):
    try:
        subprocess.run(
            [
                "shutdown",
                "/r",
                "/t",
                "5"
            ],
            check=True
        )

        return True, "Restart scheduled in 5 seconds"

    except Exception as e:
        logger.exception(
            "Failed to restart computer"
        )

        return False, str(e)


def handle_shutdown(payload):
    try:
        subprocess.run(
            [
                "shutdown",
                "/s",
                "/t",
                "5"
            ],
            check=True
        )

        return True, "Shutdown scheduled in 5 seconds"

    except Exception as e:
        logger.exception(
            "Failed to shutdown computer"
        )

        return False, str(e)


COMMAND_WHITELIST = {
    "message": handle_message,
    "lock": handle_lock,
    "restart": handle_restart,
    "shutdown": handle_shutdown,
}


def execute_command(
    command_type: str,
    payload=None
):
    handler = COMMAND_WHITELIST.get(
        command_type
    )

    if handler is None:

        logger.warning(
            f"Rejected unknown command: {command_type}"
        )

        return (
            False,
            f"Unknown or disallowed command: {command_type}"
        )

    logger.info(
        f"Executing command: {command_type}"
    )

    return handler(payload)