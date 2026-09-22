import requests
import keyring

from config import API_BASE_URL, SERVER_NAME


def get_access_token() -> str:
    """
    Authenticate the registered client agent and return
    a fresh access token.
    """

    agent_id = keyring.get_password(
        SERVER_NAME,
        "agent_id"
    )

    client_secret = keyring.get_password(
        SERVER_NAME,
        "client_secret"
    )

    if not agent_id:
        raise RuntimeError(
            "Agent ID not found. The client is not enrolled."
        )

    if not client_secret:
        raise RuntimeError(
            "Client secret not found. The client is not enrolled."
        )

    response = requests.post(
        f"{API_BASE_URL}/api/agent/auth",
        json={
            "agent_id": agent_id,
            "client_secret": client_secret
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Server did not return an access token."
        )

    return access_token