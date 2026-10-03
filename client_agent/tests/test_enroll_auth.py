
"""
Unit and integration tests for client enrollment and authentication (Phase 1).
Verifies:
- Enrollment persists server URL and credentials into CredentialStore.
- Enrollment rejects insecure HTTP in production mode.
- REST authentication sends credentials and retrieves access token using secure session.
"""

import pytest
from core.credentials import (
    BaseCredentialStore,
    get_credential_store,
    set_credential_store,
)
from server.enroll import enroll, is_enrolled
from server.auth import get_access_token


class MockCredentialStore(BaseCredentialStore):

    def __init__(self):
        self._data: dict[str, str] = {}
        self._server_url: str | None = None

    def get_credential(self, key: str) -> str | None:
        return self._data.get(key)

    def set_credential(self, key: str, value: str) -> None:
        self._data[key] = str(value)

    def delete_credential(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def is_enrolled(self) -> bool:
        return bool(
            self._data.get("agent_id")
            and self._data.get("client_secret")
            and self._data.get("computer_id")
        )

    def get_enrolled_credentials(self) -> dict | None:
        if not self.is_enrolled():
            return None
        return {
            "agent_id": self._data["agent_id"],
            "client_secret": self._data["client_secret"],
            "computer_id": int(self._data["computer_id"]),
        }

    def save_enrolled_credentials(
        self,
        agent_id: str,
        client_secret: str,
        computer_id: int,
    ) -> None:
        self.set_credential("agent_id", str(agent_id))
        self.set_credential("client_secret", str(client_secret))
        self.set_credential("computer_id", str(computer_id))

    def get_server_url(self) -> str | None:
        return self._server_url

    def set_server_url(self, server_url: str) -> None:
        self._server_url = server_url


@pytest.fixture(autouse=True)
def isolated_credential_store():
    store = MockCredentialStore()
    set_credential_store(store)
    yield store
    set_credential_store(None)


def test_enrollment_persists_credentials_and_server_url(monkeypatch):
    store = get_credential_store()
    assert is_enrolled() is False

    # Mock system info
    monkeypatch.setattr(
        "server.enroll.get_system_info",
        lambda: {
            "computer_name": "PC-TEST",
            "ip_address": "192.168.1.50",
            "mac_address": "AA:BB:CC:DD:EE:01",
            "operating_system": "Windows",
            "os_version": "11 Pro",
        },
    )

    # Mock HTTP session post response
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "agent_id": "agent-abc",
                "client_secret": "secret-xyz",
                "computer_id": 101,
            }

    class MockSession:
        def post(self, url, json, timeout):
            assert url == "https://slms.lab.edu/api/agent/register"
            assert json["enrollment_key"] == "KEY-123"
            assert json["device"]["hostname"] == "PC-TEST"
            return MockResponse()

    monkeypatch.setattr("server.enroll.create_secure_session", lambda: MockSession())

    result = enroll("KEY-123", "https://slms.lab.edu")

    assert result == {"agent_id": "agent-abc", "computer_id": 101}
    assert is_enrolled() is True
    assert store.get_server_url() == "https://slms.lab.edu"
    assert store.get_credential("agent_id") == "agent-abc"
    assert store.get_credential("computer_id") == "101"


def test_enrollment_rejects_insecure_http_in_production(monkeypatch):
    monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
    monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

    with pytest.raises(ValueError, match="Insecure HTTP URL.*is prohibited in production"):
        enroll("KEY-123", "http://insecure.lab.edu")


def test_auth_get_access_token(monkeypatch):
    store = get_credential_store()
    store.save_enrolled_credentials("agent-abc", "secret-xyz", 101)
    store.set_server_url("https://slms.lab.edu")

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "mock-jwt-token-12345"}

    class MockSession:
        def post(self, url, json, timeout):
            assert url == "https://slms.lab.edu/api/agent/auth"
            assert json["agent_id"] == "agent-abc"
            assert json["client_secret"] == "secret-xyz"
            return MockResponse()

    monkeypatch.setattr("server.auth.create_secure_session", lambda: MockSession())

    token = get_access_token()
    assert token == "mock-jwt-token-12345"


def test_auth_without_enrollment_raises_runtime_error():
    with pytest.raises(RuntimeError, match="The client is not enrolled"):
        get_access_token()


def test_enrollment_handles_http_401_403(monkeypatch):
    """Verify enrollment raises HTTPError when server rejects key with 401/403."""
    import requests

    class FailingSession:
        def post(self, url, json, timeout):
            resp = requests.Response()
            resp.status_code = 401
            resp.reason = "Unauthorized"
            resp.raise_for_status()

    monkeypatch.setattr("server.enroll.get_system_info", lambda: {
        "computer_name": "PC-TEST", "ip_address": "192.168.1.50", "mac_address": "AA:BB:CC:DD:EE:01",
        "operating_system": "Windows", "os_version": "11 Pro",
    })
    monkeypatch.setattr("server.enroll.create_secure_session", lambda: FailingSession())

    with pytest.raises(requests.exceptions.HTTPError):
        enroll("INVALID_KEY", "https://slms.lab.edu")


def test_enrollment_handles_http_500_503(monkeypatch):
    """Verify enrollment raises HTTPError when server encounters 500/503."""
    import requests

    class ServerErrorSession:
        def post(self, url, json, timeout):
            resp = requests.Response()
            resp.status_code = 503
            resp.reason = "Service Unavailable"
            resp.raise_for_status()

    monkeypatch.setattr("server.enroll.get_system_info", lambda: {
        "computer_name": "PC-TEST", "ip_address": "192.168.1.50", "mac_address": "AA:BB:CC:DD:EE:01",
        "operating_system": "Windows", "os_version": "11 Pro",
    })
    monkeypatch.setattr("server.enroll.create_secure_session", lambda: ServerErrorSession())

    with pytest.raises(requests.exceptions.HTTPError):
        enroll("KEY-123", "https://slms.lab.edu")


def test_enrollment_handles_network_timeout(monkeypatch):
    """Verify enrollment propagates requests.Timeout on network timeout."""
    import requests

    class TimeoutSession:
        def post(self, url, json, timeout):
            raise requests.exceptions.Timeout("Connection timed out after 10s")

    monkeypatch.setattr("server.enroll.get_system_info", lambda: {
        "computer_name": "PC-TEST", "ip_address": "192.168.1.50", "mac_address": "AA:BB:CC:DD:EE:01",
        "operating_system": "Windows", "os_version": "11 Pro",
    })
    monkeypatch.setattr("server.enroll.create_secure_session", lambda: TimeoutSession())

    with pytest.raises(requests.exceptions.Timeout):
        enroll("KEY-123", "https://slms.lab.edu")


def test_enrollment_handles_connection_error(monkeypatch):
    """Verify enrollment propagates requests.ConnectionError on network unreachable."""
    import requests

    class ConnectionErrorSession:
        def post(self, url, json, timeout):
            raise requests.exceptions.ConnectionError("Failed to establish a new connection")

    monkeypatch.setattr("server.enroll.get_system_info", lambda: {
        "computer_name": "PC-TEST", "ip_address": "192.168.1.50", "mac_address": "AA:BB:CC:DD:EE:01",
        "operating_system": "Windows", "os_version": "11 Pro",
    })
    monkeypatch.setattr("server.enroll.create_secure_session", lambda: ConnectionErrorSession())

    with pytest.raises(requests.exceptions.ConnectionError):
        enroll("KEY-123", "https://slms.lab.edu")


def test_auth_handles_server_error(monkeypatch):
    """Verify auth raises HTTPError on 401 or 500 responses."""
    import requests

    store = get_credential_store()
    store.save_enrolled_credentials("agent-abc", "secret-xyz", 101)
    store.set_server_url("https://slms.lab.edu")

    class FailingAuthSession:
        def post(self, url, json, timeout):
            resp = requests.Response()
            resp.status_code = 401
            resp.reason = "Unauthorized"
            resp.raise_for_status()

    monkeypatch.setattr("server.auth.create_secure_session", lambda: FailingAuthSession())

    with pytest.raises(requests.exceptions.HTTPError):
        get_access_token()


def test_upload_manager_http_401_reauth_retry(monkeypatch, tmp_path):
    """Verify UploadManager refreshes token and retries on HTTP 401."""
    from unittest.mock import MagicMock
    from requests.exceptions import HTTPError
    from core.managers import UploadManager, TokenManager, TokenHolder

    holder = TokenHolder("initial_token")
    token_mgr = TokenManager(token_holder=holder)

    refresh_called = []
    def fake_refresh():
        refresh_called.append(True)
        holder.token = "refreshed_token"
        return "refreshed_token"
    monkeypatch.setattr(token_mgr, "refresh", fake_refresh)

    upload_mgr = UploadManager()

    # Outbox is disabled to test direct HTTP upload path
    mock_outbox = MagicMock()
    mock_outbox.enabled = False
    mock_outbox.outbox = None

    send_calls = []
    def fake_send_metrics(payload, token):
        send_calls.append(token)
        if token == "initial_token":
            resp = MagicMock()
            resp.status_code = 401
            raise HTTPError("401 Unauthorized", response=resp)
        return {"status": "ok"}

    monkeypatch.setattr("core.managers._resolve_send_metrics", fake_send_metrics)

    metric_payload = {
        "hardware": {
            "cpu_usage": 15.0,
            "ram_usage": 30.0,
            "disk_usage": 45.0,
        },
        "network": {
            "bytes_sent": 1000,
            "bytes_received": 2000,
        },
    }
    success = upload_mgr.upload_metrics(metric_payload, token_mgr, mock_outbox)

    assert success is True
    assert len(refresh_called) == 1
    assert send_calls == ["initial_token", "refreshed_token"]
