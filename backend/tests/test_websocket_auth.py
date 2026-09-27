"""
Backend integration tests for WebSocket authentication migration.
Verifies target production architecture (Authorization: Bearer <token> header)
and temporary backward-compatible fallback (?token=... query parameter).
"""

import pytest
from starlette.websockets import WebSocketDisconnect


def test_websocket_auth_via_authorization_header(client, registered_agent):
    """
    Target production architecture:
    Client sends 'Authorization: Bearer <token>' header during WebSocket handshake.
    URL does NOT contain any token in the query string.
    """
    computer_id = registered_agent["computer_id"]
    token = registered_agent["token"]

    url = f"/ws/client/{computer_id}"
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(url, headers=headers) as ws:
        ws.send_text("ping")
        # Connection succeeds, heartbeat accepted without error


def test_websocket_auth_via_legacy_query_param(client, registered_agent):
    """
    Backward-compatibility verification:
    Older clients or test scripts sending '?token=...' query parameter continue working.
    """
    computer_id = registered_agent["computer_id"]
    token = registered_agent["token"]

    url = f"/ws/client/{computer_id}?token={token}"

    with client.websocket_connect(url) as ws:
        ws.send_text("ping")
        # Connection succeeds via query fallback


def test_websocket_missing_token_rejected(client, registered_agent):
    """
    Connecting with neither Authorization header nor query parameter must be rejected with code 4001.
    """
    computer_id = registered_agent["computer_id"]
    url = f"/ws/client/{computer_id}"

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass

    assert exc_info.value.code == 4001


def test_websocket_invalid_token_rejected(client, registered_agent):
    """
    Connecting with an invalid token must be rejected with code 4001.
    """
    computer_id = registered_agent["computer_id"]
    url = f"/ws/client/{computer_id}"
    headers = {"Authorization": "Bearer invalid.fake.token"}

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url, headers=headers):
            pass

    assert exc_info.value.code == 4001
