"""
Loopback Client-Backend Integration Test (J-07, J-10, J-13 / Stage 5).

Validates the full loopback lifecycle without external internet and without
touching production ProgramData or the real system state:
1. Enrollment (POST /api/agent/register)
2. Credential persistence (isolated store)
3. Agent authentication (POST /api/agent/auth -> JWT)
4. WebSocket handshake & online status tracking
5. Telemetry upload (POST /api/metrics)
6. Command dispatch over WebSocket & safe mocked execution
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure root, backend, and client_agent are on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
CLIENT_DIR = ROOT_DIR / "client_agent"

for p in [str(ROOT_DIR), str(BACKEND_DIR), str(CLIENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set test environment
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-purposes-123456789"
os.environ["DATABASE_URL"] = "sqlite:///test_slms_integration.db"
os.environ["SLMS_DEV_MODE"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.models.role import Role
from app.models.computer import Computer
from app.models.enrollment_key import EnrollmentKey
from app.models.remote_command import RemoteCommand, CommandType, CommandStatus
from app.services import command_service
from app.services.enrollment_service import create_enrollment_key
from app.websocket.connection_manager import manager
from app.auth import hash_password

from core.credentials import BaseCredentialStore, set_credential_store
from server.command_handler import execute_command


class MemoryCredentialStore(BaseCredentialStore):
    """Isolated in-memory credential store for integration tests."""

    def __init__(self):
        self._data = {}

    def get_credential(self, key: str) -> str | None:
        return self._data.get(key)

    def set_credential(self, key: str, value: str) -> None:
        self._data[key] = str(value)

    def delete_credential(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def is_enrolled(self) -> bool:
        return self.get_enrolled_credentials() is not None

    def get_enrolled_credentials(self):
        aid = self._data.get("agent_id")
        sec = self._data.get("client_secret")
        cid = self._data.get("computer_id")
        if aid and sec and cid:
            return {"agent_id": aid, "client_secret": sec, "computer_id": int(cid)}
        return None

    def save_enrolled_credentials(self, agent_id: str, client_secret: str, computer_id: int):
        self._data["agent_id"] = str(agent_id)
        self._data["client_secret"] = str(client_secret)
        self._data["computer_id"] = str(computer_id)

    def get_server_url(self) -> str | None:
        return self._data.get("server_url")

    def set_server_url(self, server_url: str):
        self._data["server_url"] = server_url


@pytest.fixture(scope="module", autouse=True)
def init_integration_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    db_file = Path("test_slms_integration.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass


@pytest.fixture
def isolated_store():
    store = MemoryCredentialStore()
    set_credential_store(store)
    yield store
    set_credential_store(None)


@pytest.mark.integration
def test_full_loopback_agent_backend_lifecycle(isolated_store):
    """
    End-to-end integration test exercising:
    Enrollment -> Persist Creds -> Authenticate -> WebSocket -> Telemetry -> Command Dispatch.
    """
    client = TestClient(app)
    db = SessionLocal()

    try:
        # Step 0: Seed Admin User & Enrollment Key
        role = Role(id=1, name="admin")
        db.add(role)
        db.commit()

        user = User(
            id=1,
            username="integ_admin",
            password_hash=hash_password("AdminPass123!"),
            role_id=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        key_record, raw_key = create_enrollment_key(db=db, created_by=user.id)

        # Step 1: Agent Enrollment (POST /api/agent/register)
        enroll_payload = {
            "enrollment_key": raw_key,
            "device": {
                "hostname": "INTEG-NODE-01",
                "ip_address": "10.0.0.42",
                "mac_address": "AA:BB:CC:11:22:33",
                "os_name": "Windows",
                "os_version": "11 Pro",
            },
        }
        enroll_resp = client.post("/api/agent/register", json=enroll_payload)
        assert enroll_resp.status_code == 201, f"Enrollment failed: {enroll_resp.text}"
        enroll_data = enroll_resp.json()
        assert "agent_id" in enroll_data
        assert "client_secret" in enroll_data
        assert "computer_id" in enroll_data

        agent_id = enroll_data["agent_id"]
        client_secret = enroll_data["client_secret"]
        computer_id = enroll_data["computer_id"]

        # Step 2: Credential Persistence (Isolated Store)
        isolated_store.save_enrolled_credentials(agent_id, client_secret, computer_id)
        isolated_store.set_server_url("http://testserver")

        loaded_creds = isolated_store.get_enrolled_credentials()
        assert loaded_creds is not None
        assert loaded_creds["agent_id"] == agent_id
        assert loaded_creds["computer_id"] == computer_id

        # Step 3: Agent Authentication (POST /api/agent/auth)
        auth_resp = client.post(
            "/api/agent/auth",
            json={"agent_id": agent_id, "client_secret": client_secret},
        )
        assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
        auth_data = auth_resp.json()
        assert "access_token" in auth_data
        access_token = auth_data["access_token"]

        # Step 4: Telemetry Upload (POST /api/metrics)
        headers = {"Authorization": f"Bearer {access_token}"}
        metric_payload = {
            "cpu_usage": 24.5,
            "ram_usage": 52.1,
            "disk_usage": 67.8,
            "network_sent": 1024,
            "network_received": 2048,
        }
        metric_resp = client.post("/api/metrics", json=metric_payload, headers=headers)
        assert metric_resp.status_code in (200, 201), f"Metrics upload failed: {metric_resp.text}"

        # Step 5: WebSocket Connection & Command Dispatch
        ws_url = f"/ws/client/{computer_id}"
        with client.websocket_connect(ws_url, headers=headers) as ws:
            assert computer_id in manager.client_connections

            # Computer status should be updated to online
            from app.models.client_status import ClientStatus
            db.expire_all()
            status_entry = db.scalar(select(ClientStatus).where(ClientStatus.computer_id == computer_id))
            assert status_entry is not None
            assert status_entry.status == "online"

            # Heartbeat ping
            ws.send_text("ping")
            assert manager.client_last_seen.get(computer_id) is not None

            # Create a pending command in backend
            cmd = RemoteCommand(
                computer_id=computer_id,
                command_type=CommandType.lock,
                payload=None,
                status=CommandStatus.pending,
                issued_by=user.id,
            )
            db.add(cmd)
            db.commit()
            db.refresh(cmd)

            # Dispatch command to active websocket
            import asyncio
            asyncio.run(command_service.dispatch_pending_commands(db, computer_id))

            # Receive command over WebSocket
            received_cmd = ws.receive_json()
            assert received_cmd["type"] == "command"
            assert received_cmd["command_type"] == "lock"

            # Execute command safely via mocked OS call
            mock_lock = MagicMock(return_value=(True, "Workstation locked"))
            with patch.dict("server.command_handler.COMMAND_WHITELIST", {"lock": mock_lock}):
                success, msg = execute_command(
                    command_type=received_cmd["command_type"],
                    payload=received_cmd.get("payload"),
                )
                assert success is True
                assert "locked" in msg.lower()
                mock_lock.assert_called_once()

    finally:
        db.close()
