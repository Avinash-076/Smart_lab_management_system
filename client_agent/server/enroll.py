"""
SLMS Client Agent Enrollment Module.

Registers this computer with the SLMS backend.
Stores credentials and persists server configuration securely.
"""

from __future__ import annotations

from enum import IntEnum
import os
import ssl
import sys
from typing import Any

import requests

from config import get_api_base_url
from core.credentials import BaseCredentialStore, get_credential_store
from core.security import (
    InsecureHttpProhibitedError,
    InvalidServerUrlError,
    create_secure_session,
    validate_and_normalize_server_url,
)
from modules.system_info import get_system_info


class EnrollmentExitCode(IntEnum):
    """
    Exit codes returned by the headless enrollment CLI.
    Enables calling installers or automation scripts to determine exact outcome.
    """
    SUCCESS = 0
    INVALID_ARGUMENT = 1
    INVALID_SERVER_URL = 2
    ALREADY_ENROLLED = 3
    INVALID_OR_EXPIRED_KEY = 4
    DUPLICATE_COMPUTER = 5
    SERVER_UNREACHABLE = 6
    TLS_SECURITY_FAILURE = 7
    ENROLLMENT_FAILURE = 8
    UNEXPECTED_ERROR = 9


def _get_target_store(store: BaseCredentialStore | None = None) -> BaseCredentialStore:
    """
    Resolve the target credential store for enrollment.
    If a store is explicitly passed, use it.
    If a test/runtime override is set (via set_credential_store), use it.
    Otherwise, default directly to ServiceCredentialStore (authoritative for Windows Service).
    """
    if store is not None:
        return store
    from core.credentials import _store_instance, ServiceCredentialStore
    if _store_instance is not None:
        return _store_instance
    return ServiceCredentialStore()


def is_enrolled(store: BaseCredentialStore | None = None) -> bool:
    """
    Check if the client has completed enrollment.
    """
    target_store = _get_target_store(store)
    return target_store.is_enrolled()


def enroll(
    enrollment_key: str,
    server_url: str | None = None,
    store: BaseCredentialStore | None = None,
) -> dict[str, Any]:
    """
    Register this computer with the SLMS backend.

    The agent_id, client_secret, computer_id, and server_url are stored
    securely via ServiceCredentialStore (or explicitly passed store).
    """
    enrollment_key = enrollment_key.strip()
    if not enrollment_key:
        raise ValueError("Enrollment key cannot be empty.")

    # Validate and normalize server URL (enforces HTTPS in production)
    if server_url and server_url.strip():
        base_url = validate_and_normalize_server_url(server_url)
    else:
        base_url = get_api_base_url()

    sys_info = get_system_info()

    device = {
        "hostname": sys_info["computer_name"],
        "ip_address": sys_info["ip_address"],
        "mac_address": sys_info["mac_address"],
        "os_name": sys_info["operating_system"],
        "os_version": sys_info["os_version"],
    }

    session = create_secure_session()
    response = session.post(
        f"{base_url}/api/agent/register",
        json={
            "enrollment_key": enrollment_key,
            "device": device,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    agent_id = data.get("agent_id")
    client_secret = data.get("client_secret")
    computer_id = data.get("computer_id")

    if not agent_id:
        raise RuntimeError("Registration response does not contain agent_id.")

    if not client_secret:
        raise RuntimeError("Registration response does not contain client_secret.")

    if computer_id is None:
        raise RuntimeError("Registration response does not contain computer_id.")

    target_store = _get_target_store(store)

    # 1. Atomic credential persistence
    try:
        target_store.save_enrolled_credentials(
            agent_id=str(agent_id),
            client_secret=str(client_secret),
            computer_id=int(computer_id),
        )
        target_store.set_server_url(base_url)
    except Exception as save_err:
        raise RuntimeError(f"Failed to persist service credentials: {save_err}") from save_err

    # 2. Post-persistence readability & integrity verification
    try:
        saved_creds = target_store.get_enrolled_credentials()
        if not saved_creds or not target_store.is_enrolled():
            raise RuntimeError("Service credentials could not be verified after write.")
        if not saved_creds.get("agent_id") or not saved_creds.get("client_secret") or saved_creds.get("computer_id") is None:
            raise RuntimeError("Persisted credentials failed data integrity verification.")
        saved_url = target_store.get_server_url()
        if not saved_url:
            raise RuntimeError("Persisted server URL could not be verified after write.")
    except Exception as verify_err:
        raise RuntimeError(f"Failed to verify persisted service credentials: {verify_err}") from verify_err

    return {
        "agent_id": agent_id,
        "computer_id": computer_id,
    }


def handle_enroll_cli(
    url: str | None = None,
    key: str | None = None,
    stdin_key: bool = False,
    key_file: str | None = None,
    force: bool = False,
    store: BaseCredentialStore | None = None,
) -> int:
    """
    Non-interactive/headless CLI enrollment handler.
    Returns an EnrollmentExitCode integer suitable for sys.exit().

    Security Invariants:
    - Never prints enrollment_key, client_secret, or JWT to stdout or stderr.
    - Never logs secrets.
    - Captures and maps all expected network, transport, auth, persistence, and conflict errors.
    """
    target_store = _get_target_store(store)
    # 1. Resolve enrollment key from inputs
    enrollment_key = ""
    try:
        if stdin_key:
            enrollment_key = sys.stdin.read().strip()
        elif key_file:
            if not os.path.isfile(key_file):
                print("Enrollment failed.", file=sys.stderr)
                print(f"Reason: Key file '{key_file}' does not exist or is not a regular file.", file=sys.stderr)
                return int(EnrollmentExitCode.INVALID_ARGUMENT)
            try:
                with open(key_file, "r", encoding="utf-8") as f:
                    enrollment_key = f.read().strip()
            except Exception as read_err:
                print("Enrollment failed.", file=sys.stderr)
                print(f"Reason: Failed to read key file '{key_file}': {read_err}", file=sys.stderr)
                return int(EnrollmentExitCode.INVALID_ARGUMENT)
        elif key:
            enrollment_key = key.strip()
        else:
            print("Enrollment failed.", file=sys.stderr)
            print("Reason: An enrollment key must be provided via --key, --stdin-key, or --key-file.", file=sys.stderr)
            return int(EnrollmentExitCode.INVALID_ARGUMENT)

        if not enrollment_key:
            print("Enrollment failed.", file=sys.stderr)
            print("Reason: Enrollment key cannot be empty.", file=sys.stderr)
            return int(EnrollmentExitCode.INVALID_ARGUMENT)

        # 2. Check already enrolled on authoritative target store
        if target_store.is_enrolled() and not force:
            print("Enrollment rejected: Workstation is already enrolled.", file=sys.stderr)
            print("Use --force to overwrite existing enrollment credentials.", file=sys.stderr)
            return int(EnrollmentExitCode.ALREADY_ENROLLED)

        # 3. Execute enrollment
        result = enroll(enrollment_key=enrollment_key, server_url=url, store=target_store)
        print("Enrollment successful.")
        print(f"Computer ID: {result.get('computer_id')}")
        return int(EnrollmentExitCode.SUCCESS)

    except InsecureHttpProhibitedError as exc:
        print("Enrollment failed.", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return int(EnrollmentExitCode.INVALID_SERVER_URL)

    except InvalidServerUrlError as exc:
        print("Enrollment failed.", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        return int(EnrollmentExitCode.INVALID_SERVER_URL)

    except (requests.exceptions.SSLError, ssl.SSLError):
        print("Enrollment failed.", file=sys.stderr)
        print("Reason: TLS/SSL verification failed. Ensure valid certificates or enterprise CA bundle are configured.", file=sys.stderr)
        return int(EnrollmentExitCode.TLS_SECURITY_FAILURE)

    except requests.exceptions.HTTPError as http_err:
        print("Enrollment failed.", file=sys.stderr)
        status_code = http_err.response.status_code if http_err.response is not None else 0
        if status_code == 401:
            print("Reason: Enrollment key is invalid, expired, or already used.", file=sys.stderr)
            return int(EnrollmentExitCode.INVALID_OR_EXPIRED_KEY)
        elif status_code == 409:
            detail = ""
            try:
                if http_err.response is not None:
                    detail = http_err.response.json().get("detail", "")
            except Exception:
                detail = ""
            detail_msg = f" ({detail})" if detail else ""
            print(f"Reason: Duplicate computer registration{detail_msg}.", file=sys.stderr)
            return int(EnrollmentExitCode.DUPLICATE_COMPUTER)
        elif status_code >= 500:
            print(f"Reason: Server returned an internal error (HTTP {status_code}).", file=sys.stderr)
            return int(EnrollmentExitCode.SERVER_UNREACHABLE)
        else:
            print(f"Reason: Server rejected registration request (HTTP {status_code}).", file=sys.stderr)
            return int(EnrollmentExitCode.ENROLLMENT_FAILURE)

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionError, TimeoutError, OSError):
        print("Enrollment failed.", file=sys.stderr)
        print("Reason: Server is unreachable. Please verify the server URL and network connectivity.", file=sys.stderr)
        return int(EnrollmentExitCode.SERVER_UNREACHABLE)

    except ValueError as ve:
        print("Enrollment failed.", file=sys.stderr)
        print(f"Reason: {ve}", file=sys.stderr)
        return int(EnrollmentExitCode.INVALID_ARGUMENT)

    except RuntimeError as re:
        print("Enrollment failed.", file=sys.stderr)
        print(f"Reason: {re}", file=sys.stderr)
        return int(EnrollmentExitCode.ENROLLMENT_FAILURE)

    except Exception:
        print("Enrollment failed.", file=sys.stderr)
        print("Reason: An unexpected error occurred during enrollment.", file=sys.stderr)
        return int(EnrollmentExitCode.UNEXPECTED_ERROR)