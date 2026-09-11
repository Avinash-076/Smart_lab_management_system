import requests
import keyring

SERVER_URL = "http://127.0.0.1:8000/api"
SERVER_NAME = "SLMS"

def get_access_token() -> str:
    agent_id = keyring.get_password(SERVER_NAME, "agent_id")
    client_secret = keyring.get_password(SERVER_NAME, "client_secret")

    response = requests.post(
        f"{SERVER_URL}/agent/auth",
        json={
            "agent_id": agent_id,
            "client_secret": client_secret
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()["access_token"]