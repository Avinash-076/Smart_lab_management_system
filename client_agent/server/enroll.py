"""
SLMS Client Agent Enrollment Module.

Registers this computer with the SLMS backend.
Stores credentials and persists server configuration securely.
"""

from __future__ import annotations

from config import get_api_base_url
from core.credentials import get_credential_store
from core.security import create_secure_session, validate_and_normalize_server_url
from modules.system_info import get_system_info


def is_enrolled() -> bool:
    """
    Check if the client has completed enrollment.
    """
    return get_credential_store().is_enrolled()


def enroll(enrollment_key: str, server_url: str | None = None) -> dict:
    """
    Register this computer with the SLMS backend.

    The agent_id, client_secret, computer_id, and server_url are stored
    securely via the CredentialStore abstraction.
    """
    enrollment_key = enrollment_key.strip()
    if not enrollment_key:
        raise ValueError("Enrollment key cannot be empty.")

    # Validate and normalize server URL (enforces HTTPS in production)
    if server_url and server_url.strip():
        base_url = validate_and_normalize_server_url(server_url)
    else:
        base_url = get_api_base_url()

    sys_info = get_system_info()

    device = {
        "hostname": sys_info["computer_name"],
        "ip_address": sys_info["ip_address"],
        "mac_address": sys_info["mac_address"],
        "os_name": sys_info["operating_system"],
        "os_version": sys_info["os_version"],
    }

    session = create_secure_session()
    response = session.post(
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
        raise RuntimeError("Registration response does not contain agent_id.")

    if not client_secret:
        raise RuntimeError("Registration response does not contain client_secret.")

    if computer_id is None:
        raise RuntimeError("Registration response does not contain computer_id.")

    store = get_credential_store()
    store.save_enrolled_credentials(
        agent_id=str(agent_id),
        client_secret=str(client_secret),
        computer_id=int(computer_id),
    )
    # Persist the validated server URL so the client communicates with the intended server
    store.set_server_url(base_url)

    return {
        "agent_id": agent_id,
        "computer_id": computer_id,
    }