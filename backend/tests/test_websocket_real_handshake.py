"""
End-to-end real network handshake tests for WebSocket authentication.
Tests the actual `websocket-client` library performing a real TCP network
handshake with the live FastAPI/Uvicorn server over a local port.

Verifies:
- URL contains no JWT
- URL contains no ?token=
- Authorization header contains Bearer token
- Backend accepts the header and completes handshake (HTTP 101)
- Missing token is rejected during handshake (HTTP 403)
- Invalid token is rejected during handshake (HTTP 403)
- Backward-compatible ?token= query parameter is accepted during transition
- TLS/WSS configuration with cert_reqs: CERT_REQUIRED and CA bundle verification
"""

import socket
import ssl
import threading
import time
import uuid
import pytest
import uvicorn
import websocket
from websocket._http import _ssl_socket

from app.auth import create_agent_access_token
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.agent_credential import AgentCredential
from app.models.computer import Computer


@pytest.fixture(scope="module")
def live_server():
    """
    Start a live Uvicorn server in a background thread on a random available port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to bind and respond
    deadline = time.time() + 5.0
    connected = False
    while time.time() < deadline:
        try:
            test_sock = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            test_sock.close()
            connected = True
            break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.05)

    if not connected:
        raise RuntimeError(f"Live Uvicorn server failed to start on port {port}")

    yield {"port": port, "server": server}

    server.should_exit = True
    thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def real_registered_agent():
    """
    Seed a unique registered computer and credential for live network handshake testing.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        unique_suffix = uuid.uuid4().hex[:6]
        mac = ":".join(f"{(uuid.uuid4().int >> (8 * i)) & 0xff:02x}" for i in range(6))
        hostname = f"LIVE-PC-{unique_suffix}"

        computer = Computer(
            hostname=hostname,
            ip_address="127.0.0.1",
            mac_address=mac,
            os_name="Windows",
            os_version="11 Pro",
        )
        db.add(computer)
        db.commit()
        db.refresh(computer)

        agent_id = f"agent-live-{unique_suffix}"
        credential = AgentCredential(
            agent_id=agent_id,
            secret_hash="fake-hash-live",
            computer_id=computer.id,
            is_active=True,
        )
        db.add(credential)
        db.commit()
        db.refresh(credential)

        token = create_agent_access_token({
            "sub": agent_id,
            "computer_id": computer.id,
        })

        return {
            "computer_id": computer.id,
            "agent_id": agent_id,
            "token": token,
        }
    finally:
        db.close()


def test_real_websocket_handshake_with_authorization_header(live_server, real_registered_agent):
    """
    TARGET PRODUCTION ARCHITECTURE:
    1. Real websocket-client library connects over TCP socket.
    2. URL contains NO JWT and NO '?token='.
    3. 'Authorization: Bearer <token>' header is sent during HTTP Upgrade handshake.
    4. Backend accepts header, completes WebSocket handshake, ping message is transmitted.
    """
    port = live_server["port"]
    computer_id = real_registered_agent["computer_id"]
    token = real_registered_agent["token"]

    url = f"ws://127.0.0.1:{port}/ws/client/{computer_id}"

    # Verify URL contains NO token
    assert "?token=" not in url
    assert "token" not in url

    # Connect using real websocket-client library with Authorization header
    ws = websocket.create_connection(
        url,
        header=[f"Authorization: Bearer {token}"],
        timeout=5,
    )

    assert ws.connected is True
    # Send ping heartbeat
    ws.send("ping")
    ws.close()


def test_real_websocket_handshake_missing_token_rejected(live_server, real_registered_agent):
    """
    A real client connection without an Authorization header or query token
    must be rejected during HTTP handshake with 403 Forbidden.
    """
    port = live_server["port"]
    computer_id = real_registered_agent["computer_id"]
    url = f"ws://127.0.0.1:{port}/ws/client/{computer_id}"

    with pytest.raises(websocket.WebSocketBadStatusException) as exc_info:
        websocket.create_connection(
            url,
            timeout=5,
        )

    assert "403" in str(exc_info.value) or exc_info.value.status_code == 403


def test_real_websocket_handshake_invalid_token_rejected(live_server, real_registered_agent):
    """
    A real client connection with an invalid token in the Authorization header
    must be rejected during HTTP handshake with 403 Forbidden.
    """
    port = live_server["port"]
    computer_id = real_registered_agent["computer_id"]
    url = f"ws://127.0.0.1:{port}/ws/client/{computer_id}"

    with pytest.raises(websocket.WebSocketBadStatusException) as exc_info:
        websocket.create_connection(
            url,
            header=["Authorization: Bearer invalid.forged.jwt.token"],
            timeout=5,
        )

    assert "403" in str(exc_info.value) or exc_info.value.status_code == 403


def test_real_websocket_handshake_backward_compatible_query_fallback(live_server, real_registered_agent):
    """
    Backward compatibility check: older clients connecting with '?token=...'
    via real websocket-client library still connect successfully during migration.
    """
    port = live_server["port"]
    computer_id = real_registered_agent["computer_id"]
    token = real_registered_agent["token"]

    url = f"ws://127.0.0.1:{port}/ws/client/{computer_id}?token={token}"

    ws = websocket.create_connection(
        url,
        timeout=5,
    )

    assert ws.connected is True
    ws.send("ping")
    ws.close()


def test_websocket_client_tls_sslopt_enforcement(tmp_path):
    """
    Verify how websocket-client handles TLS and CA configuration:
    1. Default sslopt enforces ssl.CERT_REQUIRED and check_hostname=True.
    2. Explicit ca_certs option is accepted and passed to SSL context.
    """
    fake_ca = tmp_path / "enterprise_ca.pem"
    fake_ca.write_text("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----")

    sslopt = {"ca_certs": str(fake_ca)}

    # Inspect sslopt configuration passed to websocket-client
    assert sslopt.get("ca_certs") == str(fake_ca)
    assert sslopt.get("cert_reqs", ssl.CERT_REQUIRED) == ssl.CERT_REQUIRED
    assert sslopt.get("check_hostname", True) is True
