"""
Credential storage abstraction for the SLMS Client Agent.

Phase 1 provides an abstracted interface preserving the existing Windows Keyring
storage while establishing the contract required for the future Windows Service
(e.g., machine-level DPAPI vault in Session 0) in Phase 2.
"""

from __future__ import annotations

import abc
import json
import os
from typing import Any

import keyring

from paths import CONFIG_FOLDER

DEFAULT_SERVICE_NAME = "SLMS"


class BaseCredentialStore(abc.ABC):
    """
    Abstract interface for managing client credentials and server identity.
    """

    @abc.abstractmethod
    def get_credential(self, key: str) -> str | None:
        """Retrieve a stored credential by key."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_credential(self, key: str, value: str) -> None:
        """Store a credential by key."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_credential(self, key: str) -> bool:
        """Delete a credential by key."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_enrolled(self) -> bool:
        """Check if all required enrollment credentials exist."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_enrolled_credentials(self) -> dict[str, Any] | None:
        """
        Return the dictionary of enrolled credentials:
        {"agent_id": str, "client_secret": str, "computer_id": int}
        or None if not fully enrolled.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def save_enrolled_credentials(
        self,
        agent_id: str,
        client_secret: str,
        computer_id: int,
    ) -> None:
        """Store the three core enrollment credentials."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_server_url(self) -> str | None:
        """Retrieve the persisted server URL bound during enrollment."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_server_url(self, server_url: str) -> None:
        """Persist the server URL bound during enrollment."""
        raise NotImplementedError


class KeyringCredentialStore(BaseCredentialStore):
    """
    Credential store implementation backed by Windows Keyring (Credential Manager).
    Preserves existing Phase 0 interactive user credential compatibility while
    enabling persistence of server identity.
    """

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME):
        self.service_name = service_name
        self._server_config_file = os.path.join(CONFIG_FOLDER, "server_config.json")

    def get_credential(self, key: str) -> str | None:
        return keyring.get_password(self.service_name, key)

    def set_credential(self, key: str, value: str) -> None:
        keyring.set_password(self.service_name, key, str(value))

    def delete_credential(self, key: str) -> bool:
        try:
            keyring.delete_password(self.service_name, key)
            return True
        except Exception:
            return False

    def is_enrolled(self) -> bool:
        agent_id = self.get_credential("agent_id")
        client_secret = self.get_credential("client_secret")
        computer_id = self.get_credential("computer_id")
        return bool(agent_id and client_secret and computer_id)

    def get_enrolled_credentials(self) -> dict[str, Any] | None:
        if not self.is_enrolled():
            return None

        agent_id = self.get_credential("agent_id")
        client_secret = self.get_credential("client_secret")
        computer_id_raw = self.get_credential("computer_id")

        if not agent_id or not client_secret or not computer_id_raw:
            return None

        try:
            computer_id = int(computer_id_raw)
        except (ValueError, TypeError):
            return None

        return {
            "agent_id": agent_id,
            "client_secret": client_secret,
            "computer_id": computer_id,
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
        # Check keyring first
        url = self.get_credential("server_url")
        if url:
            return url

        # Fallback to local server config file if present
        if os.path.isfile(self._server_config_file):
            try:
                with open(self._server_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("server_url")
            except Exception:
                pass
        return None

    def set_server_url(self, server_url: str) -> None:
        # Persist in keyring
        try:
            self.set_credential("server_url", server_url)
        except Exception:
            pass

        # Also persist in local server config file
        try:
            os.makedirs(os.path.dirname(self._server_config_file), exist_ok=True)
            with open(self._server_config_file, "w", encoding="utf-8") as f:
                json.dump({"server_url": server_url}, f, indent=2)
        except Exception:
            pass


_store_instance: BaseCredentialStore | None = None


def get_credential_store() -> BaseCredentialStore:
    """Return the global CredentialStore instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = KeyringCredentialStore()
    return _store_instance


def set_credential_store(store: BaseCredentialStore | None) -> None:
    """Set or override the global CredentialStore instance (useful for testing)."""
    global _store_instance
    _store_instance = store
