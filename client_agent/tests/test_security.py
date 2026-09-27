"""
Unit tests for SLMS Client Agent Security & Transport (Phase 1).
Tests URL validation, HTTPS/WSS enforcement, CA bundle configuration,
WebSocket header construction (verifying no token in URL), and student privacy.
"""

import os
import pytest

from core.security import (
    build_websocket_endpoint,
    build_websocket_headers,
    derive_ws_url,
    get_ca_bundle_path,
    get_tls_verify_parameter,
    is_insecure_http_allowed,
    validate_and_normalize_server_url,
)
from modules.system_info import get_system_info
from modules.processes import get_running_processes


class TestUrlValidation:

    def test_https_url_valid_in_production(self, monkeypatch):
        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        url = "https://slms.university.edu:8000/api"
        normalized = validate_and_normalize_server_url(url)
        assert normalized == "https://slms.university.edu:8000/api"

    def test_http_url_rejected_in_production(self, monkeypatch):
        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        with pytest.raises(ValueError, match="Insecure HTTP URL.*is prohibited in production"):
            validate_and_normalize_server_url("http://192.168.1.100:8000")

    def test_http_url_allowed_with_insecure_flag(self, monkeypatch):
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")

        normalized = validate_and_normalize_server_url("http://127.0.0.1:8000/")
        assert normalized == "http://127.0.0.1:8000"

    def test_http_url_allowed_with_dev_mode(self, monkeypatch):
        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.setenv("SLMS_DEV_MODE", "true")

        normalized = validate_and_normalize_server_url("http://localhost:8000")
        assert normalized == "http://localhost:8000"

    def test_empty_or_invalid_urls_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_and_normalize_server_url("")

        with pytest.raises(ValueError, match="Missing URL scheme"):
            validate_and_normalize_server_url("slms.university.edu")

        with pytest.raises(ValueError, match="Only HTTP and HTTPS are supported"):
            validate_and_normalize_server_url("ftp://slms.university.edu")


class TestWebSocketUrlAndHeaders:

    def test_derive_ws_url_from_https(self, monkeypatch):
        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        ws_url = derive_ws_url("https://slms.lab.edu:8000/api")
        assert ws_url == "wss://slms.lab.edu:8000/api/ws/client"

    def test_derive_ws_url_from_http_in_dev_mode(self, monkeypatch):
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        ws_url = derive_ws_url("http://127.0.0.1:8000")
        assert ws_url == "ws://127.0.0.1:8000/ws/client"

    def test_production_ws_endpoint_contains_no_token(self):
        """
        CRITICAL TEST: Verify that WebSocket endpoint URL NEVER contains ?token=
        """
        ws_base = "wss://slms.lab.edu/ws/client"
        computer_id = 42

        endpoint = build_websocket_endpoint(ws_base, computer_id)
        assert endpoint == "wss://slms.lab.edu/ws/client/42"
        assert "?token=" not in endpoint
        assert "token" not in endpoint

    def test_websocket_headers_contain_bearer_token(self):
        """
        Verify that Authorization header is built with Bearer token.
        """
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        headers = build_websocket_headers(token)

        assert headers == [f"Authorization: Bearer {token}"]

    def test_websocket_headers_reject_empty_token(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            build_websocket_headers("")


class TestTlsVerification:

    def test_verify_parameter_defaults_to_true(self, monkeypatch):
        monkeypatch.delenv("SLMS_CA_BUNDLE", raising=False)
        param = get_tls_verify_parameter()
        assert param is True
        assert param is not False

    def test_ca_bundle_returns_valid_path(self, monkeypatch, tmp_path):
        fake_ca = tmp_path / "custom_ca.pem"
        fake_ca.write_text("-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----")

        monkeypatch.setenv("SLMS_CA_BUNDLE", str(fake_ca))
        assert get_ca_bundle_path() == str(fake_ca)
        assert get_tls_verify_parameter() == str(fake_ca)

    def test_missing_ca_bundle_raises_file_not_found(self, monkeypatch):
        monkeypatch.setenv("SLMS_CA_BUNDLE", "C:\\nonexistent_ca_path_12345.pem")
        with pytest.raises(FileNotFoundError, match="does not exist"):
            get_ca_bundle_path()


class TestPrivacyHardening:

    def test_system_info_does_not_collect_username(self):
        """
        SRS requirement: Student personal data (Windows username) must not be collected.
        """
        info = get_system_info()
        assert "username" not in info, "Windows username must not be collected in system_info"

    def test_processes_sets_user_to_none(self):
        """
        SRS requirement: Process owner username must not be collected.
        """
        processes = get_running_processes()
        # Verify that for any processes returned, 'user' is None
        for p in processes[:10]:
            assert p.get("user") is None, f"Process username must be None, got {p.get('user')}"


class TestServerUrlBinding:

    def test_enrolled_server_url_authoritative_in_production(self, monkeypatch):
        from config import get_api_base_url
        from core.credentials import BaseCredentialStore, set_credential_store

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
        monkeypatch.delenv("SLMS_API_URL", raising=False)

        class MockEnrolledStore(BaseCredentialStore):
            def get_credential(self, key): return None
            def set_credential(self, key, value): pass
            def delete_credential(self, key): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self): return {}
            def save_enrolled_credentials(self, a, c, comp): pass
            def get_server_url(self): return "https://authoritative.lab.edu:8000"
            def set_server_url(self, u): pass

        set_credential_store(MockEnrolledStore())
        try:
            assert get_api_base_url() == "https://authoritative.lab.edu:8000"
        finally:
            set_credential_store(None)

    def test_enrolled_server_cannot_be_silently_overridden_in_production(self, monkeypatch):
        """
        REGRESSION TEST: In production, SLMS_API_URL must NOT silently redirect
        an enrolled agent to another server. A RuntimeError must be raised.
        """
        from config import get_api_base_url
        from core.credentials import BaseCredentialStore, set_credential_store

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
        monkeypatch.setenv("SLMS_API_URL", "https://rogue-server.attacker.com:8000")

        class MockEnrolledStore(BaseCredentialStore):
            def get_credential(self, key): return None
            def set_credential(self, key, value): pass
            def delete_credential(self, key): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self): return {}
            def save_enrolled_credentials(self, a, c, comp): pass
            def get_server_url(self): return "https://authoritative.lab.edu:8000"
            def set_server_url(self, u): pass

        set_credential_store(MockEnrolledStore())
        try:
            with pytest.raises(RuntimeError, match="Cannot override enrolled server URL.*in production"):
                get_api_base_url()
        finally:
            set_credential_store(None)

    def test_enrolled_server_matching_env_url_accepted(self, monkeypatch):
        from config import get_api_base_url
        from core.credentials import BaseCredentialStore, set_credential_store

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
        monkeypatch.setenv("SLMS_API_URL", "https://authoritative.lab.edu:8000/")

        class MockEnrolledStore(BaseCredentialStore):
            def get_credential(self, key): return None
            def set_credential(self, key, value): pass
            def delete_credential(self, key): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self): return {}
            def save_enrolled_credentials(self, a, c, comp): pass
            def get_server_url(self): return "https://authoritative.lab.edu:8000"
            def set_server_url(self, u): pass

        set_credential_store(MockEnrolledStore())
        try:
            assert get_api_base_url() == "https://authoritative.lab.edu:8000"
        finally:
            set_credential_store(None)

    def test_enrolled_server_override_allowed_in_dev_mode(self, monkeypatch):
        from config import get_api_base_url
        from core.credentials import BaseCredentialStore, set_credential_store

        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.setenv("SLMS_API_URL", "http://127.0.0.1:9000")

        class MockEnrolledStore(BaseCredentialStore):
            def get_credential(self, key): return None
            def set_credential(self, key, value): pass
            def delete_credential(self, key): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self): return {}
            def save_enrolled_credentials(self, a, c, comp): pass
            def get_server_url(self): return "https://authoritative.lab.edu:8000"
            def set_server_url(self, u): pass

        set_credential_store(MockEnrolledStore())
        try:
            assert get_api_base_url() == "http://127.0.0.1:9000"
        finally:
            set_credential_store(None)

    def test_ws_base_url_cannot_be_overridden_in_production(self, monkeypatch):
        from config import get_ws_base_url
        from core.credentials import BaseCredentialStore, set_credential_store

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
        monkeypatch.setenv("SLMS_WS_URL", "wss://rogue.attacker.com/ws/client")

        class MockEnrolledStore(BaseCredentialStore):
            def get_credential(self, key): return None
            def set_credential(self, key, value): pass
            def delete_credential(self, key): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self): return {}
            def save_enrolled_credentials(self, a, c, comp): pass
            def get_server_url(self): return "https://authoritative.lab.edu:8000"
            def set_server_url(self, u): pass

        set_credential_store(MockEnrolledStore())
        try:
            with pytest.raises(RuntimeError, match="cannot be overridden by SLMS_WS_URL.*in production"):
                get_ws_base_url()
        finally:
            set_credential_store(None)

