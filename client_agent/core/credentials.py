"""
Credential storage abstraction for the SLMS Client Agent.

Phase 1 provided an abstracted interface preserving the existing Windows Keyring
storage for interactive user sessions.
Phase 2 introduces `ServiceCredentialStore` (DPAPI machine-scope protected storage)
which enables the Windows Service in Session 0 to access enrolled credentials
across reboots without requiring any user or student login.
"""

from __future__ import annotations

import abc
import ctypes
from ctypes import wintypes
import json
import os
import subprocess
from typing import Any

import keyring

import logging

from paths import get_data_dir, CONFIG_FOLDER

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_NAME = "SLMS"
DEFAULT_ENTROPY = b"SLMS_AGENT_SERVICE_DPAPI_ENTROPY_V2"


# ============================================================================
# DPAPI Machine Scope Helpers
# ============================================================================

class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def is_dpapi_available() -> bool:
    """Check if Windows DPAPI (crypt32.dll) is available on this system."""
    if os.environ.get("SLMS_MOCK_DPAPI") == "1":
        return False
    try:
        return hasattr(ctypes, "windll") and hasattr(ctypes.windll, "crypt32")
    except Exception:
        return False


def dpapi_encrypt(data: bytes, entropy: bytes = DEFAULT_ENTROPY) -> bytes:
    """
    Encrypt bytes using Windows DPAPI machine scope (CRYPTPROTECT_LOCAL_MACHINE).
    Combines DPAPI with application entropy to ensure only callers with the
    correct entropy can decrypt the data.
    """
    if not is_dpapi_available():
        # Fallback test mock cipher for non-Windows / mocked environments
        return b"MOCK_DPAPI:" + bytes([b ^ 0x5A for b in data])

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB(
        len(data),
        ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)),
    )
    out_blob = DATA_BLOB()

    entropy_blob_ptr = None
    if entropy:
        entropy_blob = DATA_BLOB(
            len(entropy),
            ctypes.cast(ctypes.create_string_buffer(entropy), ctypes.POINTER(ctypes.c_char)),
        )
        entropy_blob_ptr = ctypes.byref(entropy_blob)

    # CRYPTPROTECT_LOCAL_MACHINE = 0x4
    res = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "SLMS_Service_Credentials",
        entropy_blob_ptr,
        None,
        None,
        0x4,
        ctypes.byref(out_blob),
    )
    if res == 0:
        error_code = ctypes.GetLastError()
        raise OSError(f"CryptProtectData failed with error code: {error_code}")

    ciphertext = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    kernel32.LocalFree(out_blob.pbData)
    return ciphertext


def dpapi_decrypt(ciphertext: bytes, entropy: bytes = DEFAULT_ENTROPY) -> bytes:
    """
    Decrypt bytes using Windows DPAPI machine scope (CRYPTPROTECT_LOCAL_MACHINE).
    Requires the matching entropy used during encryption.
    """
    if not is_dpapi_available() or ciphertext.startswith(b"MOCK_DPAPI:"):
        raw = ciphertext.removeprefix(b"MOCK_DPAPI:")
        return bytes([b ^ 0x5A for b in raw])

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB(
        len(ciphertext),
        ctypes.cast(ctypes.create_string_buffer(ciphertext), ctypes.POINTER(ctypes.c_char)),
    )
    out_blob = DATA_BLOB()

    entropy_blob_ptr = None
    if entropy:
        entropy_blob = DATA_BLOB(
            len(entropy),
            ctypes.cast(ctypes.create_string_buffer(entropy), ctypes.POINTER(ctypes.c_char)),
        )
        entropy_blob_ptr = ctypes.byref(entropy_blob)

    res = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        entropy_blob_ptr,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if res == 0:
        error_code = ctypes.GetLastError()
        raise OSError(f"CryptUnprotectData failed with error code: {error_code}")

    plaintext = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    kernel32.LocalFree(out_blob.pbData)
    return plaintext


# ============================================================================
# Credential Store Interfaces & Implementations
# ============================================================================

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
    Interactive Credential Store implementation backed by Windows Keyring (Credential Manager).
    Suitable for interactive desktop execution and local development.
    """

    def __init__(self, service_name: str = DEFAULT_SERVICE_NAME, config_folder: str | None = None):
        self.service_name = service_name
        self.config_folder = config_folder if config_folder is not None else os.path.join(get_data_dir(), "config")
        self._server_config_file = os.path.join(self.config_folder, "server_config.json")

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
        url = self.get_credential("server_url")
        if url:
            return url

        if os.path.isfile(self._server_config_file):
            try:
                with open(self._server_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("server_url")
            except Exception:
                pass
        return None

    def set_server_url(self, server_url: str) -> None:
        try:
            self.set_credential("server_url", server_url)
        except Exception:
            pass

        try:
            os.makedirs(os.path.dirname(self._server_config_file), exist_ok=True)
            with open(self._server_config_file, "w", encoding="utf-8") as f:
                json.dump({"server_url": server_url}, f, indent=2)
        except Exception:
            pass


# Alias for explicit clarity in Phase 2
InteractiveCredentialStore = KeyringCredentialStore


class ServiceCredentialStore(BaseCredentialStore):
    """
    Service Credential Store implementation backed by Windows DPAPI Machine Scope
    with application entropy and NTFS ACL protection.

    Solves the Session 0 problem: credentials persisted via this store can be read
    by the Windows Service (e.g. running under NT SERVICE\\SLMSService or LocalSystem)
    without requiring any user or student login.
    """

    def __init__(
        self,
        config_folder: str | None = None,
        entropy: bytes = DEFAULT_ENTROPY,
    ):
        self.config_folder = config_folder if config_folder is not None else os.path.join(get_data_dir(), "config")
        self.entropy = entropy
        self.credential_file = os.path.join(self.config_folder, "service_credentials.enc")
        self._server_config_file = os.path.join(self.config_folder, "server_config.json")

    def _read_payload(self) -> dict[str, Any]:
        """Read and decrypt the stored credentials payload."""
        if not os.path.isfile(self.credential_file):
            return {}

        try:
            with open(self.credential_file, "rb") as f:
                ciphertext = f.read()
            if not ciphertext:
                return {}

            plaintext = dpapi_decrypt(ciphertext, self.entropy)
            return json.loads(plaintext.decode("utf-8"))
        except PermissionError as pe:
            logger.error(
                f"Permission denied reading service credential file '{self.credential_file}': {pe}. "
                "Ensure NT SERVICE\\SLMSService (or the active service account) has Read permissions."
            )
            return {}
        except Exception as e:
            logger.warning(f"Failed to read/decrypt service credentials from '{self.credential_file}': {e}")
            return {}

    def _write_payload(self, data: dict[str, Any]) -> None:
        """Encrypt and write the credentials payload with restricted permissions."""
        os.makedirs(self.config_folder, exist_ok=True)
        raw_bytes = json.dumps(data).encode("utf-8")
        ciphertext = dpapi_encrypt(raw_bytes, self.entropy)

        # Write to temporary file first then atomically replace
        tmp_file = f"{self.credential_file}.tmp"
        with open(tmp_file, "wb") as f:
            f.write(ciphertext)

        if os.path.exists(self.credential_file):
            os.remove(self.credential_file)
        os.replace(tmp_file, self.credential_file)

        # Attempt to restrict file ACL to Administrators and SYSTEM
        self._set_restricted_permissions(self.credential_file)

    def _set_restricted_permissions(self, filepath: str) -> None:
        """
        Attempt to restrict file permissions to Administrators, SYSTEM,
        and current user/service via icacls.
        Prevents unprivileged students from reading the DPAPI ciphertext.
        """
        if os.name != "nt":
            return
        try:
            username = os.environ.get("USERNAME", "")
            cmd = [
                "icacls",
                filepath,
                "/inheritance:r",
                "/grant:r",
                "*S-1-5-32-544:(F)",  # Builtin Administrators
                "/grant:r",
                "*S-1-5-18:(F)",      # LocalSystem
            ]
            if username:
                cmd.extend(["/grant:r", f"{username}:(F)"])
            subprocess.run(
                cmd,
                capture_output=True,
                check=False,
                timeout=5,
            )
            # Attempt to grant service account Read permission if service already exists in SCM.
            # If the service does not exist yet (as during pre-service fresh headless enrollment),
            # this step safely proceeds; the subsequent service install lifecycle will establish
            # the mandatory service ACL after sc.exe create succeeds.
            res_svc = subprocess.run(
                ["icacls", filepath, "/grant", r"NT SERVICE\SLMSService:(R)"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if res_svc.returncode == 0:
                logger.debug(f"Granted NT SERVICE\\SLMSService Read permission on {filepath}.")
            else:
                logger.debug(
                    f"Notice: Pre-service creation ACL assignment for NT SERVICE\\SLMSService exited with {res_svc.returncode}. "
                    "Service installation lifecycle will apply mandatory credential ACL after service creation."
                )
        except Exception as e:
            logger.debug(f"_set_restricted_permissions notice: {e}")

    def grant_service_account_access(self, service_account: str = "NT SERVICE\\SLMSService") -> bool:
        """
        Explicitly grant the specified Windows service account Read permission on the credential file.
        Returns True on success, False if icacls fails.
        """
        if os.name != "nt" or not service_account or service_account.lower() == "localsystem":
            return True

        if not os.path.isfile(self.credential_file):
            logger.warning(f"Cannot grant service ACL: credential file does not exist at {self.credential_file}")
            return False

        try:
            cmd = ["icacls", self.credential_file, "/grant", f"{service_account}:(R)"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=5)
            if res.returncode == 0:
                logger.info(f"Granted {service_account} Read permission on {self.credential_file}.")
                return True
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logger.error(f"Failed to grant {service_account} Read on {self.credential_file}: {err}")
                return False
        except Exception as e:
            logger.error(f"Error executing icacls on {self.credential_file}: {e}")
            return False

    def get_credential(self, key: str) -> str | None:
        payload = self._read_payload()
        val = payload.get(key)
        return str(val) if val is not None else None

    def set_credential(self, key: str, value: str) -> None:
        payload = self._read_payload()
        payload[key] = str(value)
        self._write_payload(payload)

    def delete_credential(self, key: str) -> bool:
        payload = self._read_payload()
        if key in payload:
            del payload[key]
            self._write_payload(payload)
            return True
        return False

    def is_enrolled(self) -> bool:
        creds = self.get_enrolled_credentials()
        return creds is not None

    def get_enrolled_credentials(self) -> dict[str, Any] | None:
        payload = self._read_payload()
        agent_id = payload.get("agent_id")
        client_secret = payload.get("client_secret")
        computer_id = payload.get("computer_id")

        if not agent_id or not client_secret or computer_id is None:
            return None

        try:
            return {
                "agent_id": str(agent_id),
                "client_secret": str(client_secret),
                "computer_id": int(computer_id),
            }
        except (ValueError, TypeError):
            return None

    def save_enrolled_credentials(
        self,
        agent_id: str,
        client_secret: str,
        computer_id: int,
    ) -> None:
        payload = self._read_payload()
        payload["agent_id"] = str(agent_id)
        payload["client_secret"] = str(client_secret)
        payload["computer_id"] = int(computer_id)
        self._write_payload(payload)

    def get_server_url(self) -> str | None:
        payload = self._read_payload()
        url = payload.get("server_url")
        if url:
            return str(url)

        if os.path.isfile(self._server_config_file):
            try:
                with open(self._server_config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("server_url")
            except Exception:
                pass
        return None

    def set_server_url(self, server_url: str) -> None:
        payload = self._read_payload()
        payload["server_url"] = str(server_url)
        self._write_payload(payload)

        try:
            os.makedirs(os.path.dirname(self._server_config_file), exist_ok=True)
            with open(self._server_config_file, "w", encoding="utf-8") as f:
                json.dump({"server_url": server_url}, f, indent=2)
        except Exception:
            pass

    def clear(self) -> None:
        """Remove the encrypted service credentials file."""
        if os.path.isfile(self.credential_file):
            try:
                os.remove(self.credential_file)
            except Exception:
                pass


# Alias for explicit clarity in Phase 2
DpapiCredentialStore = ServiceCredentialStore


# ============================================================================
# Credential Migration Helper
# ============================================================================

def migrate_credentials(
    source_store: BaseCredentialStore,
    destination_store: BaseCredentialStore,
) -> bool:
    """
    Migrate enrolled credentials and server URL from one store to another.
    Enables interactive administrator enrollment to provision credentials
    directly for the background Windows Service.
    """
    if not source_store.is_enrolled():
        return False

    creds = source_store.get_enrolled_credentials()
    if not creds:
        return False

    destination_store.save_enrolled_credentials(
        agent_id=creds["agent_id"],
        client_secret=creds["client_secret"],
        computer_id=creds["computer_id"],
    )

    server_url = source_store.get_server_url()
    if server_url:
        destination_store.set_server_url(server_url)

    return True


# ============================================================================
# Global Store Resolution
# ============================================================================

_store_instance: BaseCredentialStore | None = None


def get_credential_store() -> BaseCredentialStore:
    """
    Resolve the active CredentialStore instance with the following priority:
    1. Explicitly configured test or runtime store (via set_credential_store).
    2. KeyringCredentialStore if SLMS_USE_KEYRING=1 (unless in explicit service mode).
    3. ServiceCredentialStore by default for Windows Service, headless enrollment, and production.

    Note: SLMS_DEV_MODE strictly controls logging/debugging behavior and MUST NOT
    determine credential-store selection.
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    use_keyring = os.environ.get("SLMS_USE_KEYRING", "0").lower() in ("1", "true", "yes")
    service_mode = os.environ.get("SLMS_SERVICE_MODE", "0").lower() in ("1", "true", "yes")

    if use_keyring and not service_mode:
        return KeyringCredentialStore()

    return ServiceCredentialStore()


def set_credential_store(store: BaseCredentialStore | None) -> None:
    """Set or override the global CredentialStore instance (useful for testing)."""
    global _store_instance
    _store_instance = store
