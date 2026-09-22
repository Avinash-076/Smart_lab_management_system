import requests
import keyring

from modules.system_info import get_system_info
from config import API_BASE_URL, SERVER_NAME


def is_enrolled() -> bool:
    agent_id = keyring.get_password(SERVER_NAME, "agent_id")
    client_secret = keyring.get_password(SERVER_NAME, "client_secret")
    computer_id = keyring.get_password(SERVER_NAME, "computer_id")

    return bool(agent_id and client_secret and computer_id)


def enroll(enrollment_key: str, server_url: str | None = None):
    """
    Register this computer with the SLMS backend.

    The agent_id, client_secret and computer_id returned by
    the server are stored securely in Windows Keyring.
    """

    enrollment_key = enrollment_key.strip()

    if not enrollment_key:
        raise ValueError("Enrollment key cannot be empty.")

    # Use the URL entered in the GUI if provided.
    base_url = (server_url or API_BASE_URL).rstrip("/")

    sys_info = get_system_info()

    device = {
        "hostname": sys_info["computer_name"],
        "ip_address": sys_info["ip_address"],
        "mac_address": sys_info["mac_address"],
        "os_name": sys_info["operating_system"],
        "os_version": sys_info["os_version"],
    }

    response = requests.post(
        f"{base_url}/api/agent/register",
        json={
            "enrollment_key": enrollment_key,
            "device": device,
        },
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    agent_id = data.get("agent_id")
    client_secret = data.get("client_secret")
    computer_id = data.get("computer_id")

    if not agent_id:
        raise RuntimeError(
            "Registration response does not contain agent_id."
        )

    if not client_secret:
        raise RuntimeError(
            "Registration response does not contain client_secret."
        )

    if computer_id is None:
        raise RuntimeError(
            "Registration response does not contain computer_id."
        )

    # Store credentials in Windows Keyring.
    keyring.set_password(
        SERVER_NAME,
        "agent_id",
        str(agent_id),
    )

    keyring.set_password(
        SERVER_NAME,
        "client_secret",
        str(client_secret),
    )

    keyring.set_password(
        SERVER_NAME,
        "computer_id",
        str(computer_id),
    )

    return {
        "agent_id": agent_id,
        "computer_id": computer_id,
    }