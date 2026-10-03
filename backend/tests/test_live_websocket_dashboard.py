import json
import pytest
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.websocket.connection_manager import manager


@pytest.fixture
def dashboard_auth_user(db_session):
    # Ensure role with VIEW_COMPUTERS exists
    role = db_session.scalars(select(Role).where(Role.name == "Admin")).first()
    if not role:
        role = Role(name="Admin")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    perm = db_session.scalars(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.action_code == "VIEW_COMPUTERS",
        )
    ).first()
    if not perm:
        perm = RolePermission(role_id=role.id, action_code="VIEW_COMPUTERS", allowed=True)
        db_session.add(perm)
        db_session.commit()

    user = db_session.scalars(select(User).where(User.username == "ws_test_admin")).first()
    if not user:
        user = User(
            username="ws_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def unauthorized_dashboard_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "RestrictedRole")).first()
    if not role:
        role = Role(name="RestrictedRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "ws_restricted_user")).first()
    if not user:
        user = User(
            username="ws_restricted_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


def test_dashboard_websocket_authenticated_connect(client, dashboard_auth_user):
    """
    Authenticated user with VIEW_COMPUTERS permission connects successfully.
    """
    token = dashboard_auth_user["token"]
    url = f"/ws/dashboard?token={token}"

    with client.websocket_connect(url) as ws:
        assert len(manager.dashboard_connections) == 1

    # On exit / disconnect, connection is removed cleanly
    assert len(manager.dashboard_connections) == 0


def test_dashboard_websocket_auth_header(client, dashboard_auth_user):
    """
    Dashboard WebSocket connects via Authorization: Bearer <token> header.
    """
    token = dashboard_auth_user["token"]
    url = "/ws/dashboard"
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(url, headers=headers) as ws:
        assert len(manager.dashboard_connections) == 1

    assert len(manager.dashboard_connections) == 0


def test_dashboard_websocket_missing_token_rejected(client):
    """
    Unauthenticated WebSocket connection is rejected with code 4001.
    """
    url = "/ws/dashboard"

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass

    assert exc_info.value.code == 4001


def test_dashboard_websocket_invalid_token_rejected(client):
    """
    Connection with invalid token is rejected with code 4001.
    """
    url = "/ws/dashboard?token=invalid.jwt.token"

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass

    assert exc_info.value.code == 4001


def test_dashboard_websocket_missing_permission_rejected(client, unauthorized_dashboard_user):
    """
    User missing VIEW_COMPUTERS permission is rejected with code 4003.
    """
    token = unauthorized_dashboard_user["token"]
    url = f"/ws/dashboard?token={token}"

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(url):
            pass

    assert exc_info.value.code == 4003


def test_dashboard_receives_metric_update_broadcast(client, dashboard_auth_user, registered_agent):
    """
    When a metric is uploaded via POST /api/metrics, connected dashboards receive metric_update.
    """
    token = dashboard_auth_user["token"]
    agent_token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]

    url = f"/ws/dashboard?token={token}"

    with client.websocket_connect(url) as ws:
        # Ingest a metric
        metric_payload = {
            "cpu_usage": 45.2,
            "ram_usage": 62.8,
            "disk_usage": 51.0,
            "network_sent": 12.5,
            "network_received": 34.0,
        }
        res = client.post(
            "/api/metrics",
            headers={"Authorization": f"Bearer {agent_token}"},
            json=metric_payload,
        )
        assert res.status_code == 201

        # Receive WebSocket message
        msg_text = ws.receive_text()
        msg = json.loads(msg_text)

        assert msg["type"] == "metric_update"
        assert msg["computer_id"] == computer_id
        assert msg["cpu_usage"] == 45.2
        assert msg["ram_usage"] == 62.8
        assert msg["disk_usage"] == 51.0
        assert "recorded_at" in msg


def test_dashboard_receives_status_update_on_client_connect(
    client, dashboard_auth_user, registered_agent
):
    """
    When client agent connects to /ws/client/{id}, status_update online is broadcast.
    """
    token = dashboard_auth_user["token"]
    agent_token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]

    dashboard_url = f"/ws/dashboard?token={token}"
    client_ws_url = f"/ws/client/{computer_id}?token={agent_token}"

    with client.websocket_connect(dashboard_url) as dash_ws:
        # Connect client agent
        with client.websocket_connect(client_ws_url):
            # Dashboard receives "online" status update
            online_msg_raw = dash_ws.receive_text()
            online_msg = json.loads(online_msg_raw)
            assert online_msg["type"] == "status_update"
            assert online_msg["computer_id"] == computer_id
            assert online_msg["status"] == "online"


def test_dashboard_receives_status_update_broadcast(
    client, dashboard_auth_user, registered_agent
):
    """
    When status update is broadcast, connected dashboards receive status_update message.
    """
    token = dashboard_auth_user["token"]
    computer_id = registered_agent["computer_id"]

    dashboard_url = f"/ws/dashboard?token={token}"

    with client.websocket_connect(dashboard_url) as dash_ws:
        import asyncio

        asyncio.run(
            manager.broadcast_to_dashboards(
                {
                    "type": "status_update",
                    "computer_id": computer_id,
                    "status": "offline",
                }
            )
        )

        msg_raw = dash_ws.receive_text()
        msg = json.loads(msg_raw)
        assert msg["type"] == "status_update"
        assert msg["computer_id"] == computer_id
        assert msg["status"] == "offline"

