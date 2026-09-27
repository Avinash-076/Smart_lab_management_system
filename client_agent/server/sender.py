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
    Preserves cumulative network byte counter contract and passes idempotency_key if present.

    D-01 / D-02 Hardening:
    Does NOT convert collector failures into valid numeric 0 values.
    If hardware collection failed or is missing, raises ValueError.
    Network byte counters allow None on failure, preserving distinguishability.
    """
    from core.health import CollectionResult

    if "cpu_usage" in data and ("ram_usage" in data or "ram_percent" in data):
        payload = {
            "cpu_usage": float(data["cpu_usage"]),
            "ram_usage": float(data.get("ram_usage", data.get("ram_percent", 0.0))),
            "disk_usage": float(data.get("disk_usage", data.get("disk_percent", 0.0))),
            "network_sent": data.get("network_sent"),
            "network_received": data.get("network_received"),
        }
        if "idempotency_key" in data:
            payload["idempotency_key"] = data["idempotency_key"]
        return payload

    hardware_entry = data.get("hardware")
    if isinstance(hardware_entry, CollectionResult):
        if hardware_entry.is_failed:
            raise ValueError(f"Hardware metrics collection failed: {hardware_entry.error}")
        hardware = hardware_entry.data or {}
    elif hardware_entry is None:
        raise ValueError("Hardware metrics are unavailable; cannot build metric payload.")
    else:
        hardware = hardware_entry

    network_entry = data.get("network")
    if isinstance(network_entry, CollectionResult):
        if network_entry.is_failed:
            network_sent = None
            network_received = None
        else:
            net_data = network_entry.data or {}
            network_sent = net_data.get("bytes_sent")
            network_received = net_data.get("bytes_received")
    elif isinstance(network_entry, dict):
        network_sent = network_entry.get("bytes_sent")
        network_received = network_entry.get("bytes_received")
    else:
        network_sent = None
        network_received = None

    cpu_val = hardware.get("cpu_usage")
    if cpu_val is None:
        raise ValueError("Missing cpu_usage in hardware data; cannot fabricate 0% metric.")

    payload = {
        "cpu_usage": float(cpu_val),
        "ram_usage": float(hardware.get("ram_percent", hardware.get("ram_usage", 0.0))),
        "disk_usage": float(hardware.get("disk_percent", hardware.get("disk_usage", 0.0))),
        "network_sent": network_sent,
        "network_received": network_received,
    }
    if "idempotency_key" in data:
        payload["idempotency_key"] = data["idempotency_key"]
    return payload



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

def send_software_inventory(data: dict | list, access_token: str) -> list:
    """
    Send installed software inventory to the backend.
    """
    if isinstance(data, list):
        software = data
    else:
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

def send_process_inventory(data: dict | list, access_token: str) -> list:
    """
    Send currently running processes to the backend.
    """
    if isinstance(data, list):
        processes = data
    else:
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

def send_usage_sessions(data: dict | list, access_token: str) -> list:
    """
    Send completed application usage sessions to the backend.
    """
    if isinstance(data, list):
        sessions = data
    else:
        sessions = data.get("usage") or data.get("sessions") or []
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
    if "idempotency_key" in issue and issue["idempotency_key"]:
        payload["idempotency_key"] = issue["idempotency_key"]
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


# ==========================================
# Command Results
# ==========================================

def send_command_result(command_id: int, payload: dict, access_token: str) -> dict:
    """
    Send remote command execution result to the backend.
    """
    api_url = get_api_base_url()
    session = create_secure_session()

    response = session.post(
        f"{api_url}/api/commands/{command_id}/result",
        json=payload,
        headers=_build_headers(access_token),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
