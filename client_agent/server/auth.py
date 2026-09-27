"""
SLMS Client Agent Authentication Module.

Handles token acquisition and renewal with the backend using secure TLS transport.
"""

from __future__ import annotations

from config import get_api_base_url
from core.credentials import get_credential_store
from core.security import create_secure_session


def get_access_token() -> str:
    """
    Authenticate the registered client agent and return a fresh access token.
    Uses strict TLS verification and persisted server identity.
    """
    store = get_credential_store()
    agent_id = store.get_credential("agent_id")
    client_secret = store.get_credential("client_secret")

    if not agent_id:
        raise RuntimeError("Agent ID not found. The client is not enrolled.")

    if not client_secret:
        raise RuntimeError("Client secret not found. The client is not enrolled.")

    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/agent/auth",
        json={
            "agent_id": agent_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError("Server did not return an access token.")

    return access_token