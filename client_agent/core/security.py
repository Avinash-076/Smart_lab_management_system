"""
Security and transport utilities for the SLMS Client Agent.

Enforces HTTPS/WSS in production, strict TLS verification (never verify=False),
optional enterprise CA bundle support, and secure header-based WebSocket authentication.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import requests


def is_insecure_http_allowed() -> bool:
    """
    Check if plaintext HTTP/WS communication is permitted.
    Only allowed when explicitly enabled via environment variables
    for local development or testing.
    """
    val = os.getenv("SLMS_ALLOW_INSECURE_HTTP", "").strip().lower()
    dev_val = os.getenv("SLMS_DEV_MODE", "").strip().lower()
    return val in ("1", "true", "yes") or dev_val in ("1", "true", "yes")


def validate_and_normalize_server_url(
    url: str,
    allow_insecure: bool | None = None,
) -> str:
    """
    Validate and normalize an SLMS server URL.

    - Strips trailing slashes and whitespace.
    - Requires valid hostname.
    - Enforces HTTPS in production unless allow_insecure is True.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Server URL cannot be empty.")

    clean_url = url.strip().rstrip("/")
    if not clean_url:
        raise ValueError("Server URL cannot be empty.")

    parsed = urlparse(clean_url)
    if not parsed.scheme:
        raise ValueError(
            f"Invalid server URL '{url}': Missing URL scheme (expected https://)."
        )

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid server URL scheme '{scheme}': Only HTTP and HTTPS are supported."
        )

    if allow_insecure is None:
        allow_insecure = is_insecure_http_allowed()

    if scheme == "http" and not allow_insecure:
        raise ValueError(
            f"Insecure HTTP URL '{url}' is prohibited in production. "
            "Production SLMS communication requires HTTPS. "
            "Set SLMS_ALLOW_INSECURE_HTTP=1 only for local development."
        )

    if not parsed.netloc:
        raise ValueError(
            f"Invalid server URL '{url}': Must contain a valid hostname or IP address."
        )

    path = parsed.path.rstrip("/")
    return f"{scheme}://{parsed.netloc}{path}"


def derive_ws_url(
    api_url: str,
    allow_insecure: bool | None = None,
) -> str:
    """
    Derive the corresponding WebSocket endpoint base URL from the REST API base URL.
    https:// -> wss://
    http:// -> ws:// (only if insecure is permitted)
    """
    normalized_api = validate_and_normalize_server_url(api_url, allow_insecure=allow_insecure)
    parsed = urlparse(normalized_api)

    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    path = parsed.path.rstrip("/")
    ws_path = f"{path}/ws/client" if path else "/ws/client"
    return f"{ws_scheme}://{parsed.netloc}{ws_path}"


def get_ca_bundle_path() -> str | None:
    """
    Return the path to an enterprise CA bundle if configured via SLMS_CA_BUNDLE.
    Verifies that the file exists.
    """
    ca_bundle = os.getenv("SLMS_CA_BUNDLE", "").strip()
    if not ca_bundle:
        return None

    if not os.path.isfile(ca_bundle):
        raise FileNotFoundError(
            f"Configured CA bundle file does not exist: '{ca_bundle}'"
        )

    return ca_bundle


def get_tls_verify_parameter() -> str | bool:
    """
    Return the parameter to pass to requests(verify=...) or similar clients.
    Returns custom CA bundle path if configured, or True.
    CRITICAL SECURITY INVARIANT: NEVER RETURNS FALSE.
    """
    ca_bundle = get_ca_bundle_path()
    if ca_bundle:
        return ca_bundle
    return True


def create_secure_session() -> requests.Session:
    """
    Create a requests Session configured with strict TLS verification.
    """
    session = requests.Session()
    session.verify = get_tls_verify_parameter()
    return session


def build_websocket_endpoint(ws_base_url: str, computer_id: int) -> str:
    """
    Construct the WebSocket connection URL.
    CRITICAL SECURITY INVARIANT: DOES NOT INCLUDE JWT TOKENS IN THE URL QUERY STRING.
    Target production architecture format: {ws_base_url}/{computer_id}
    """
    base = ws_base_url.strip().rstrip("/")
    return f"{base}/{computer_id}"


def build_websocket_headers(access_token: str) -> list[str]:
    """
    Build standard Authorization header for WebSocket handshake.
    Format: 'Authorization: Bearer <token>'
    """
    if not access_token:
        raise ValueError("Access token cannot be empty.")
    return [f"Authorization: Bearer {access_token}"]
