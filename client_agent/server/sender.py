import requests

from config import API_BASE_URL


# ==========================================
# Common Headers
# ==========================================

def _build_headers(
    access_token: str,
) -> dict:
    """
    Build standard authenticated API headers.
    """

    return {
        "Authorization": (
            f"Bearer {access_token}"
        ),
        "Content-Type": "application/json",
    }


# ==========================================
# Metrics
# ==========================================

def build_metric_payload(
    data: dict,
) -> dict:
    """
    Convert collected client data into the payload
    expected by the SLMS metrics API.
    """

    hardware = data.get(
        "hardware"
    ) or {}

    network = data.get(
        "network"
    ) or {}

    return {
        "cpu_usage": hardware.get(
            "cpu_usage",
            0,
        ),
        "ram_usage": hardware.get(
            "ram_percent",
            0,
        ),
        "disk_usage": hardware.get(
            "disk_percent",
            0,
        ),
        "network_sent": network.get(
            "bytes_sent",
            0,
        ),
        "network_received": network.get(
            "bytes_received",
            0,
        ),
    }


def send_metrics(
    data: dict,
    access_token: str,
) -> dict:
    """
    Send current system metrics to the backend.
    """

    payload = build_metric_payload(
        data
    )

    response = requests.post(
        f"{API_BASE_URL}/api/metrics",
        json=payload,
        headers=_build_headers(
            access_token
        ),
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# Software Inventory
# ==========================================

def send_software_inventory(
    data: dict,
    access_token: str,
) -> list:
    """
    Send installed software inventory to the backend.
    """

    software = data.get(
        "software"
    ) or []

    payload = {
        "software": software
    }

    response = requests.post(
        f"{API_BASE_URL}/api/software",
        json=payload,
        headers=_build_headers(
            access_token
        ),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# Process Monitoring
# ==========================================

def send_process_inventory(
    data: dict,
    access_token: str,
) -> list:
    """
    Send currently running processes to the backend.
    """

    processes = data.get(
        "processes"
    ) or []

    payload = {
        "processes": processes
    }

    response = requests.post(
        f"{API_BASE_URL}/api/processes",
        json=payload,
        headers=_build_headers(
            access_token
        ),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# Usage History
# ==========================================

def send_usage_sessions(
    data: dict,
    access_token: str,
) -> list:
    """
    Send completed application usage sessions
    to the backend.
    """

    sessions = data.get(
        "usage"
    ) or []

    if not sessions:
        return []

    payload = {
        "sessions": sessions
    }

    response = requests.post(
        f"{API_BASE_URL}/api/usage",
        json=payload,
        headers=_build_headers(
            access_token
        ),
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# Issue Reporting
# ==========================================

def send_issue(
    issue: dict,
    access_token: str,
) -> dict:
    """
    Send one automatically detected issue
    to the agent issue endpoint.

    Backend endpoint:

        POST /api/issues/agent

    The backend automatically identifies the
    computer from the agent credentials.
    """

    payload = {
        "title": issue["title"],
        "description": issue["description"],
        "severity": issue["severity"],
    }

    response = requests.post(
        f"{API_BASE_URL}/api/issues/agent",
        json=payload,
        headers=_build_headers(
            access_token
        ),
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def send_issues(
    issues: list[dict],
    access_token: str,
) -> list[dict]:
    """
    Send multiple automatically detected issues.

    Each issue is sent individually because the
    backend currently exposes one-issue-per-request
    through /api/issues/agent.
    """

    results: list[dict] = []

    for issue in issues:

        result = send_issue(
            issue,
            access_token,
        )

        results.append(
            result
        )

    return results