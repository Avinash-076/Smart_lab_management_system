"""
SLMS Client Agent REST Sender Module.

Transmits metrics, inventories, usage sessions, and issues to the backend.
Uses secure TLS transport, enterprise CA bundle configuration, and validated server URLs.
"""

from __future__ import annotations

from config import get_api_base_url
from core.security import create_secure_session


# ==========================================
# Common Headers
# ==========================================

def _build_headers(access_token: str) -> dict:
    """
    Build standard authenticated API headers.
    """
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


# ==========================================
# Metrics
# ==========================================

def build_metric_payload(data: dict) -> dict:
    """
    Convert collected client data into the payload expected by the SLMS metrics API.
    Preserves cumulative network byte counter contract.
    """
    hardware = data.get("hardware") or {}
    network = data.get("network") or {}

    return {
        "cpu_usage": hardware.get("cpu_usage", 0),
        "ram_usage": hardware.get("ram_percent", 0),
        "disk_usage": hardware.get("disk_percent", 0),
        "network_sent": network.get("bytes_sent", 0),
        "network_received": network.get("bytes_received", 0),
    }


def send_metrics(data: dict, access_token: str) -> dict:
    """
    Send current system metrics to the backend.
    """
    payload = build_metric_payload(data)
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/metrics",
        json=payload,
        headers=_build_headers(access_token),
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# ==========================================
# Software Inventory
# ==========================================

def send_software_inventory(data: dict, access_token: str) -> list:
    """
    Send installed software inventory to the backend.
    """
    software = data.get("software") or []
    payload = {"software": software}
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/software",
        json=payload,
        headers=_build_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ==========================================
# Process Monitoring
# ==========================================

def send_process_inventory(data: dict, access_token: str) -> list:
    """
    Send currently running processes to the backend.
    """
    processes = data.get("processes") or []
    payload = {"processes": processes}
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/processes",
        json=payload,
        headers=_build_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ==========================================
# Usage History
# ==========================================

def send_usage_sessions(data: dict, access_token: str) -> list:
    """
    Send completed application usage sessions to the backend.
    """
    sessions = data.get("usage") or []
    if not sessions:
        return []

    payload = {"sessions": sessions}
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/usage",
        json=payload,
        headers=_build_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ==========================================
# Issue Reporting
# ==========================================

def send_issue(issue: dict, access_token: str) -> dict:
    """
    Send one automatically detected issue to the agent issue endpoint.
    """
    payload = {
        "title": issue["title"],
        "description": issue["description"],
        "severity": issue["severity"],
    }
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/issues/agent",
        json=payload,
        headers=_build_headers(access_token),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def send_issues(issues: list[dict], access_token: str) -> list[dict]:
    """
    Send multiple automatically detected issues.
    """
    results: list[dict] = []
    for issue in issues:
        result = send_issue(issue, access_token)
        results.append(result)
    return results