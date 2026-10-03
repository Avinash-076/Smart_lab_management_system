"""
Unit tests for SLMS Client Agent CredentialStore abstraction (Phase 1).
Tests credential storage, enrollment status check, and server URL persistence.
"""

import pytest
from core.credentials import (
    BaseCredentialStore,
    KeyringCredentialStore,
    get_credential_store,
    set_credential_store,
)


class InMemoryCredentialStore(BaseCredentialStore):
    """Mock store for clean isolated unit testing."""

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


class TestCredentialStoreAbstraction:

    @pytest.fixture(autouse=True)
    def setup_store(self):
        mock_store = InMemoryCredentialStore()
        set_credential_store(mock_store)
        yield mock_store
        set_credential_store(None)

    def test_not_enrolled_initially(self):
        store = get_credential_store()
        assert store.is_enrolled() is False
        assert store.get_enrolled_credentials() is None

    def test_save_and_retrieve_credentials(self):
        store = get_credential_store()
        store.save_enrolled_credentials("agent-123", "secret-456", 10)

        assert store.is_enrolled() is True
        creds = store.get_enrolled_credentials()
        assert creds == {
            "agent_id": "agent-123",
            "client_secret": "secret-456",
            "computer_id": 10,
        }

    def test_partial_credentials_not_enrolled(self):
        store = get_credential_store()
        store.set_credential("agent_id", "agent-123")
        store.set_credential("computer_id", "10")
        # client_secret is missing
        assert store.is_enrolled() is False
        assert store.get_enrolled_credentials() is None

    def test_server_url_persistence(self):
        store = get_credential_store()
        assert store.get_server_url() is None

        store.set_server_url("https://slms.lab.edu:8000")
        assert store.get_server_url() == "https://slms.lab.edu:8000"


class TestKeyringCredentialStoreServerConfig:

    def test_keyring_store_file_fallback(self, tmp_path, monkeypatch):
        """
        Verify that KeyringCredentialStore falls back to server_config.json
        if server_url is not in keyring.
        """
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))

        store = KeyringCredentialStore(service_name="TEST_SLMS", config_folder=str(config_dir))
        monkeypatch.setattr(store, "get_credential", lambda key: None)

        # Before writing, server_url is None
        assert store.get_server_url() is None

        # Set server_url
        store.set_server_url("https://slms.test.edu:8443")

        # Now get_server_url should read from the file
        assert store.get_server_url() == "https://slms.test.edu:8443"


class TestCredentialStoreResolution:
    """Verify get_credential_store resolution priority and decoupling from SLMS_DEV_MODE."""

    def test_default_resolves_service_store(self, monkeypatch):
        """By default without env vars, get_credential_store() returns ServiceCredentialStore."""
        set_credential_store(None)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
        monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)

        store = get_credential_store()
        from core.credentials import ServiceCredentialStore
        assert isinstance(store, ServiceCredentialStore)

    def test_dev_mode_does_not_select_keyring(self, monkeypatch):
        """SLMS_DEV_MODE=1 strictly controls logging and MUST NOT select KeyringCredentialStore."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)

        store = get_credential_store()
        from core.credentials import ServiceCredentialStore
        assert isinstance(store, ServiceCredentialStore)

    def test_use_keyring_selects_keyring(self, monkeypatch):
        """SLMS_USE_KEYRING=1 selects KeyringCredentialStore for interactive development."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_USE_KEYRING", "1")
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)

        store = get_credential_store()
        from core.credentials import KeyringCredentialStore
        assert isinstance(store, KeyringCredentialStore)

    def test_service_mode_overrides_use_keyring(self, monkeypatch):
        """SLMS_SERVICE_MODE=1 always forces ServiceCredentialStore even if SLMS_USE_KEYRING=1."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_USE_KEYRING", "1")
        monkeypatch.setenv("SLMS_SERVICE_MODE", "1")

        store = get_credential_store()
        from core.credentials import ServiceCredentialStore
        assert isinstance(store, ServiceCredentialStore)
