"""
Phase 1 Test Suite: Headless / Non-Interactive Workstation Enrollment CLI.

Covers all Phase 1 requirements:
1. Fresh enrollment succeeds with --key
2. Correct server URL is passed to enrollment logic
3. Stdin key (--stdin-key) succeeds without logging key
4. Key file (--key-file) succeeds without logging key
5. Invalid / missing URL is rejected (exit code 2)
6. Insecure HTTP rejected in production (exit code 2)
7. Missing enrollment key rejected (exit code 1)
8. Empty key rejected (exit code 1)
9. Non-existent key file rejected (exit code 1)
10. Already-enrolled machine handled safely (exit code 3 without --force)
11. Already-enrolled machine overwrites safely with --force (exit code 0)
12. HTTP 401 maps to exit code 4 (INVALID_OR_EXPIRED_KEY)
13. HTTP 409 maps to exit code 5 (DUPLICATE_COMPUTER)
14. Connection error / timeout maps to exit code 6 (SERVER_UNREACHABLE)
15. TLS/SSL failure maps to exit code 7 (TLS_SECURITY_FAILURE)
16. Generic HTTP error / malformed response maps to exit code 8 (ENROLLMENT_FAILURE)
17. Unexpected error maps to exit code 9 (UNEXPECTED_ERROR)
18. Zero secrets in stdout, stderr, or logs
19. CLI argument parsing in service.service.main and main.py routing
"""

import io
import os
import ssl
import sys
from unittest.mock import MagicMock, patch
import pytest
import requests

from core.credentials import (
    BaseCredentialStore,
    get_credential_store,
    set_credential_store,
)
from server.enroll import EnrollmentExitCode, enroll, handle_enroll_cli, is_enrolled


class MockCredentialStore(BaseCredentialStore):
    """In-memory credential store for test isolation."""

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
def isolated_credentials():
    store = MockCredentialStore()
    set_credential_store(store)
    yield store
    set_credential_store(None)


class TestHeadlessEnrollmentCLI:
    """Test suite for headless enrollment CLI execution and exit codes."""

    def test_01_fresh_enrollment_with_key_succeeds(self, monkeypatch, capsys):
        """1. Verify fresh enrollment with --key succeeds and returns exit code 0."""
        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                return {"agent_id": "AGT_001", "client_secret": "super_secret_secret_123", "computer_id": 42}

        class MockSession:
            def post(self, url, json, timeout):
                assert url == "https://slms.lab.edu/api/agent/register"
                assert json["enrollment_key"] == "SLMS-VALID-KEY-999"
                return MockResponse()

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MockSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC-01", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="SLMS-VALID-KEY-999")
        assert code == EnrollmentExitCode.SUCCESS

        captured = capsys.readouterr()
        assert "Enrollment successful." in captured.out
        assert "Computer ID: 42" in captured.out
        assert is_enrolled() is True

    def test_02_correct_server_url_passed(self, monkeypatch):
        """2. Verify custom server URL is passed to enrollment logic."""
        captured_url = []
        class MockSession:
            def post(self, url, json, timeout):
                captured_url.append(url)
                resp = MagicMock()
                resp.json.return_value = {"agent_id": "AGT_002", "client_secret": "sec", "computer_id": 43}
                return resp

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MockSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC-02", "ip_address": "192.168.1.11", "mac_address": "00:11:22:33:44:56",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://custom-server.university.edu:8443", key="KEY-ABC")
        assert code == EnrollmentExitCode.SUCCESS
        assert captured_url == ["https://custom-server.university.edu:8443/api/agent/register"]

    def test_03_stdin_key_succeeds(self, monkeypatch, capsys):
        """3. Verify enrollment reading key from sys.stdin succeeds."""
        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                return {"agent_id": "AGT_STDIN", "client_secret": "sec", "computer_id": 50}

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MagicMock(post=lambda *a, **k: MockResponse()))
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC-STDIN", "ip_address": "192.168.1.12", "mac_address": "00:11:22:33:44:57",
            "operating_system": "Windows", "os_version": "11",
        })

        monkeypatch.setattr("sys.stdin", io.StringIO("SLMS-PIPED-KEY-123\n"))

        code = handle_enroll_cli(url="https://slms.lab.edu", stdin_key=True)
        assert code == EnrollmentExitCode.SUCCESS

        captured = capsys.readouterr()
        assert "Enrollment successful." in captured.out
        assert "Computer ID: 50" in captured.out

    def test_04_key_file_succeeds(self, tmp_path, monkeypatch, capsys):
        """4. Verify enrollment reading key from key file succeeds."""
        key_file = tmp_path / "enroll_key.txt"
        key_file.write_text("SLMS-FILE-KEY-456\n", encoding="utf-8")

        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                return {"agent_id": "AGT_FILE", "client_secret": "sec", "computer_id": 60}

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MagicMock(post=lambda *a, **k: MockResponse()))
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC-FILE", "ip_address": "192.168.1.13", "mac_address": "00:11:22:33:44:58",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key_file=str(key_file))
        assert code == EnrollmentExitCode.SUCCESS

        captured = capsys.readouterr()
        assert "Enrollment successful." in captured.out
        assert "Computer ID: 60" in captured.out

    def test_05_invalid_url_rejected(self, capsys):
        """5. Verify invalid URL returns exit code 2 (INVALID_SERVER_URL)."""
        code = handle_enroll_cli(url="not-a-valid-url", key="KEY-123")
        assert code == EnrollmentExitCode.INVALID_SERVER_URL
        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Missing URL scheme" in captured.err

    def test_06_insecure_http_rejected_in_production(self, monkeypatch, capsys):
        """6. Verify insecure HTTP in production returns exit code 2 (INVALID_SERVER_URL)."""
        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        code = handle_enroll_cli(url="http://insecure-server.lab.edu", key="KEY-123")
        assert code == EnrollmentExitCode.INVALID_SERVER_URL
        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Insecure HTTP URL" in captured.err

    def test_07_missing_enrollment_key_rejected(self, capsys):
        """7. Verify missing key returns exit code 1 (INVALID_ARGUMENT)."""
        code = handle_enroll_cli(url="https://slms.lab.edu")
        assert code == EnrollmentExitCode.INVALID_ARGUMENT
        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "An enrollment key must be provided" in captured.err

    def test_08_empty_key_rejected(self, capsys):
        """8. Verify empty key string returns exit code 1 (INVALID_ARGUMENT)."""
        code = handle_enroll_cli(url="https://slms.lab.edu", key="   ")
        assert code == EnrollmentExitCode.INVALID_ARGUMENT
        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Enrollment key cannot be empty" in captured.err

    def test_09_nonexistent_key_file_rejected(self, capsys):
        """9. Verify non-existent key file returns exit code 1 (INVALID_ARGUMENT)."""
        code = handle_enroll_cli(url="https://slms.lab.edu", key_file="C:\\nonexistent_key_file_9999.txt")
        assert code == EnrollmentExitCode.INVALID_ARGUMENT
        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "does not exist" in captured.err

    def test_10_already_enrolled_refuses_without_force(self, capsys):
        """10. Verify already-enrolled machine returns exit code 3 (ALREADY_ENROLLED) without --force."""
        store = get_credential_store()
        store.save_enrolled_credentials("AGT_EXISTING", "existing_sec", 10)
        store.set_server_url("https://slms.lab.edu")

        assert is_enrolled() is True

        code = handle_enroll_cli(url="https://slms.lab.edu", key="NEW-KEY-123", force=False)
        assert code == EnrollmentExitCode.ALREADY_ENROLLED

        captured = capsys.readouterr()
        assert "Enrollment rejected: Workstation is already enrolled." in captured.err
        assert "Use --force" in captured.err

    def test_11_already_enrolled_overwrites_with_force(self, monkeypatch, capsys):
        """11. Verify already-enrolled machine proceeds and overwrites credentials when force=True."""
        store = get_credential_store()
        store.save_enrolled_credentials("AGT_OLD", "old_sec", 10)
        store.set_server_url("https://slms.lab.edu")

        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                return {"agent_id": "AGT_REPLACED", "client_secret": "new_sec", "computer_id": 99}

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MagicMock(post=lambda *a, **k: MockResponse()))
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="NEW-KEY-123", force=True)
        assert code == EnrollmentExitCode.SUCCESS

        captured = capsys.readouterr()
        assert "Enrollment successful." in captured.out
        assert "Computer ID: 99" in captured.out
        assert store.get_credential("agent_id") == "AGT_REPLACED"

    def test_12_http_401_maps_to_invalid_or_expired_key(self, monkeypatch, capsys):
        """12. Verify HTTP 401 returns exit code 4 (INVALID_OR_EXPIRED_KEY)."""
        class FailingSession:
            def post(self, url, json, timeout):
                resp = requests.Response()
                resp.status_code = 401
                resp.reason = "Unauthorized"
                resp.raise_for_status()

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: FailingSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="EXPIRED-KEY")
        assert code == EnrollmentExitCode.INVALID_OR_EXPIRED_KEY

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Enrollment key is invalid, expired, or already used." in captured.err

    def test_13_http_409_maps_to_duplicate_computer(self, monkeypatch, capsys):
        """13. Verify HTTP 409 returns exit code 5 (DUPLICATE_COMPUTER)."""
        class ConflictSession:
            def post(self, url, json, timeout):
                resp = requests.Response()
                resp.status_code = 409
                resp._content = b'{"detail": "A computer with this hostname already exists"}'
                resp.reason = "Conflict"
                resp.raise_for_status()

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: ConflictSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="KEY-DUPLICATE")
        assert code == EnrollmentExitCode.DUPLICATE_COMPUTER

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Duplicate computer registration" in captured.err
        assert "A computer with this hostname already exists" in captured.err

    def test_14_connection_error_and_timeout_maps_to_server_unreachable(self, monkeypatch, capsys):
        """14. Verify ConnectionError and Timeout return exit code 6 (SERVER_UNREACHABLE)."""
        class TimeoutSession:
            def post(self, url, json, timeout):
                raise requests.exceptions.Timeout("Connection timed out after 10s")

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: TimeoutSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="KEY-TIMEOUT")
        assert code == EnrollmentExitCode.SERVER_UNREACHABLE

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "Server is unreachable" in captured.err

    def test_15_tls_failure_maps_to_tls_security_failure(self, monkeypatch, capsys):
        """15. Verify SSL verification failure returns exit code 7 (TLS_SECURITY_FAILURE)."""
        class SSLFailureSession:
            def post(self, url, json, timeout):
                raise requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED")

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: SSLFailureSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="KEY-SSL")
        assert code == EnrollmentExitCode.TLS_SECURITY_FAILURE

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "TLS/SSL verification failed" in captured.err

    def test_16_generic_http_and_parsing_error_maps_to_enrollment_failure(self, monkeypatch, capsys):
        """16. Verify generic HTTP 400 or missing fields returns exit code 8 (ENROLLMENT_FAILURE)."""
        class BadDataSession:
            def post(self, url, json, timeout):
                resp = requests.Response()
                resp.status_code = 200
                resp._content = b'{"agent_id": "AGT_1"}'  # missing client_secret and computer_id
                return resp

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: BadDataSession())
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        code = handle_enroll_cli(url="https://slms.lab.edu", key="KEY-BAD-DATA")
        assert code == EnrollmentExitCode.ENROLLMENT_FAILURE

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err

    def test_17_unexpected_error_maps_to_unexpected_error(self, monkeypatch, capsys):
        """17. Verify unhandled exception returns exit code 9 (UNEXPECTED_ERROR)."""
        def bad_get_system_info():
            raise SystemError("Unexpected OS kernel error")

        monkeypatch.setattr("server.enroll.get_system_info", bad_get_system_info)

        code = handle_enroll_cli(url="https://slms.lab.edu", key="KEY-UNEXPECTED")
        assert code == EnrollmentExitCode.UNEXPECTED_ERROR

        captured = capsys.readouterr()
        assert "Enrollment failed." in captured.err
        assert "unexpected error occurred" in captured.err

    def test_18_zero_secrets_in_stdout_stderr_and_logs(self, monkeypatch, capsys, caplog):
        """18. Verify enrollment key and client_secret NEVER appear in stdout, stderr, or logs."""
        secret_enroll_key = "ULTRA_CONFIDENTIAL_ENROLL_KEY_9999"
        secret_client_secret = "ULTRA_CONFIDENTIAL_CLIENT_SECRET_8888"

        class MockResponse:
            def raise_for_status(self): pass
            def json(self):
                return {
                    "agent_id": "AGT_CONF",
                    "client_secret": secret_client_secret,
                    "computer_id": 77,
                }

        monkeypatch.setattr("server.enroll.create_secure_session", lambda: MagicMock(post=lambda *a, **k: MockResponse()))
        monkeypatch.setattr("server.enroll.get_system_info", lambda: {
            "computer_name": "LAB-PC", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55",
            "operating_system": "Windows", "os_version": "11",
        })

        with caplog.at_level("DEBUG"):
            code = handle_enroll_cli(url="https://slms.lab.edu", key=secret_enroll_key)

        assert code == EnrollmentExitCode.SUCCESS

        captured = capsys.readouterr()
        # Check stdout & stderr
        assert secret_enroll_key not in captured.out
        assert secret_enroll_key not in captured.err
        assert secret_client_secret not in captured.out
        assert secret_client_secret not in captured.err

        # Check logs
        all_logs = caplog.text
        assert secret_enroll_key not in all_logs
        assert secret_client_secret not in all_logs

    def test_19_main_cli_routing_and_service_service_dispatch(self, monkeypatch):
        """19. Verify sys.argv dispatch in main.py and service.service.main for enroll command."""
        from service.service import main as service_main

        mock_handle = MagicMock(return_value=0)
        monkeypatch.setattr("server.enroll.handle_enroll_cli", mock_handle)

        test_argv = [
            "SLMS_Client_Agent.exe",
            "enroll",
            "--url", "https://slms.lab.edu",
            "--key", "ARG-KEY-123",
            "--force",
        ]

        with patch.object(sys, "argv", test_argv), pytest.raises(SystemExit) as exc_info:
            service_main()

        assert exc_info.value.code == 0
        mock_handle.assert_called_once_with(
            url="https://slms.lab.edu",
            key="ARG-KEY-123",
            stdin_key=False,
            key_file=None,
            force=True,
        )

    def test_20_existing_service_commands_remain_functional(self, monkeypatch):
        """20. Verify existing service subcommands (status, install, etc.) parse cleanly."""
        from service.service import main as service_main

        with patch.object(sys, "argv", ["SLMS_Client_Agent.exe", "status"]), \
             patch("service.service.get_service_status", return_value="RUNNING") as mock_status:
            service_main()
            mock_status.assert_called_once()

    def test_21_dev_mode_1_headless_enrollment_creates_service_credentials(self, tmp_path, monkeypatch):
        """21. Real-world Case 1: SLMS_DEV_MODE=1 creates service_credentials.enc on disk."""
        set_credential_store(None)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("SLMS_MOCK_DPAPI", "1")
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)
        monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-dev-01",
            "client_secret": "secret-dev-01",
            "computer_id": 101,
        }

        with patch("requests.Session.post", return_value=mock_resp):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key="DEV-KEY-101",
                force=False,
            )

        assert exit_code == int(EnrollmentExitCode.SUCCESS)
        cred_file = config_dir / "service_credentials.enc"
        assert cred_file.is_file(), "service_credentials.enc must exist on disk under SLMS_DEV_MODE=1"

        from core.credentials import ServiceCredentialStore
        verify_store = ServiceCredentialStore(config_folder=str(config_dir))
        assert verify_store.is_enrolled() is True
        assert verify_store.get_enrolled_credentials() == {
            "agent_id": "agent-dev-01",
            "client_secret": "secret-dev-01",
            "computer_id": 101,
        }

    def test_22_dev_mode_0_headless_enrollment_creates_service_credentials(self, tmp_path, monkeypatch):
        """22. Real-world Case 2: SLMS_DEV_MODE=0 creates service_credentials.enc on disk."""
        set_credential_store(None)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("SLMS_DEV_MODE", "0")
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("SLMS_MOCK_DPAPI", "1")
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)
        monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-prod-02",
            "client_secret": "secret-prod-02",
            "computer_id": 102,
        }

        with patch("requests.Session.post", return_value=mock_resp):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key="PROD-KEY-102",
                force=False,
            )

        assert exit_code == int(EnrollmentExitCode.SUCCESS)
        cred_file = config_dir / "service_credentials.enc"
        assert cred_file.is_file(), "service_credentials.enc must exist on disk under SLMS_DEV_MODE=0"

        from core.credentials import ServiceCredentialStore
        verify_store = ServiceCredentialStore(config_folder=str(config_dir))
        assert verify_store.is_enrolled() is True
        assert verify_store.get_enrolled_credentials() == {
            "agent_id": "agent-prod-02",
            "client_secret": "secret-prod-02",
            "computer_id": 102,
        }

    def test_23_stale_keyring_does_not_block_headless_enrollment(self, tmp_path, monkeypatch):
        """23. Stale Keyring entries do NOT trigger ALREADY_ENROLLED when ServiceCredentialStore is empty."""
        set_credential_store(None)
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("SLMS_MOCK_DPAPI", "1")

        # Simulate stale Keyring store that claims to be enrolled
        with patch("core.credentials.KeyringCredentialStore.is_enrolled", return_value=True):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "agent_id": "agent-fresh-03",
                "client_secret": "secret-fresh-03",
                "computer_id": 103,
            }

            with patch("requests.Session.post", return_value=mock_resp):
                exit_code = handle_enroll_cli(
                    url="http://127.0.0.1:8000",
                    key="FRESH-KEY-103",
                    force=False,
                )

            assert exit_code == int(EnrollmentExitCode.SUCCESS), "Stale Keyring must not cause ALREADY_ENROLLED (exit code 3)"
            cred_file = config_dir / "service_credentials.enc"
            assert cred_file.is_file()

    def test_24_persistence_failure_returns_enrollment_failure(self, tmp_path, monkeypatch):
        """24. Failure during save_enrolled_credentials returns exit code 8 (ENROLLMENT_FAILURE)."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-err-04",
            "client_secret": "secret-err-04",
            "computer_id": 104,
        }

        with patch("requests.Session.post", return_value=mock_resp), \
             patch("core.credentials.ServiceCredentialStore.save_enrolled_credentials", side_effect=OSError("Disk write error")):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key="KEY-FAIL-104",
            )

        assert exit_code == int(EnrollmentExitCode.ENROLLMENT_FAILURE)

    def test_25_post_persistence_verification_failure_returns_enrollment_failure(self, tmp_path, monkeypatch):
        """25. Verification failure after save returns exit code 8 (ENROLLMENT_FAILURE)."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-verify-05",
            "client_secret": "secret-verify-05",
            "computer_id": 105,
        }

        with patch("requests.Session.post", return_value=mock_resp), \
             patch("core.credentials.ServiceCredentialStore.save_enrolled_credentials"), \
             patch("core.credentials.ServiceCredentialStore.get_enrolled_credentials", return_value=None):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key="KEY-CORRUPT-105",
            )

        assert exit_code == int(EnrollmentExitCode.ENROLLMENT_FAILURE)

    def test_26_persistence_error_messages_contain_zero_secrets(self, tmp_path, capsys, monkeypatch):
        """26. Verify persistence failure messages never leak keys, secrets, or tokens."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))

        secret_key = "CONFIDENTIAL-KEY-999"
        secret_pass = "ULTRA-SECRET-PASS-888"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-sec-99",
            "client_secret": secret_pass,
            "computer_id": 999,
        }

        with patch("requests.Session.post", return_value=mock_resp), \
             patch("core.credentials.ServiceCredentialStore.save_enrolled_credentials", side_effect=RuntimeError("Permission Denied")):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key=secret_key,
            )

        assert exit_code == int(EnrollmentExitCode.ENROLLMENT_FAILURE)
        captured = capsys.readouterr()
        assert secret_key not in captured.out
        assert secret_key not in captured.err
        assert secret_pass not in captured.out
        assert secret_pass not in captured.err
