import ctypes
import os
import subprocess
from logger import logger

def handle_message(payload):
    try:
        ctypes.windll.user32.MessageBoxW(0, payload or "Message from administrator", "SLMS Notice", 0x40)
        return True, "Message displayed"

    except Exception as e:
        return False, str(e)

def handle_lock(payload):
    try:
        ctypes.windll.user32.LockWorkStation()
        return True, "Workstation locked"

    except Exception as e:
        return False, str(e)

def handle_restart(payload):
    try:
        subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
        return True, "Restart scheduled in 5 seconds"

    except Exception as e:
        return False, str(e)

def handle_shutdown(payload):
    try:
        subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
        return True, "Shutdown scheduled in 5 seconds"

    except Exception as e:
        return False, str(e)

COMMAND_WHITELIST = {
    "message": handle_message,
    "lock": handle_lock,
    "restart": handle_restart,
    "shutdonw": handle_shutdown,
}

def execute_command(command_type: str, payload):
    handler = COMMAND_WHITELIST.get(command_type)
    if handler is None:
        logger.warning(f"Rejected unknown command type: {command_type}")
        return False, f"Unknown or disallowed command: {command_type}"

    logger.info(f"Executing command: {command_type}")
    return handler(payload)
    
