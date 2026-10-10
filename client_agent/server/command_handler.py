import ctypes
import subprocess

from core.logger import logger


def handle_message(payload):
    """
    Handle administrative message notice.
    Service-safe architecture: Eliminates Session 0 MessageBoxW calls.
    Broadcasts message to active user desktop sessions via msg.exe if available,
    and records the notice in the agent log.
    """
    raw_message = str(payload).strip() if payload else "Message from administrator"
    # Truncate to reasonable maximum length (1024 chars) to prevent command-line buffer issues
    message = raw_message[:1024] if len(raw_message) > 1024 else raw_message
    logger.info(f"Administrator notice received: {message}")

    # Attempt to broadcast to active interactive user sessions via Windows msg.exe
    try:
        result = subprocess.run(
            ["msg", "*", "/time:15", message],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            return True, "Notice broadcast to interactive user session(s)"
        else:
            logger.debug(
                f"msg.exe returned code {result.returncode}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug(f"msg.exe broadcast unavailable or timed out: {exc}")
    except Exception as exc:
        logger.debug(f"msg.exe unexpected error: {exc}")

    # Non-interactive fallback: notice was safely recorded in agent logs
    return True, f"Notice recorded in agent log: {message}"



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

    try:
        success, message = handler(payload)
    except Exception as exc:
        logger.exception(
            f"Unhandled exception in command handler for '{command_type}': {exc}"
        )
        success, message = False, f"Execution exception: {exc}"

    if message and len(message) > 255:
        message = message[:252] + "..."

    return success, message