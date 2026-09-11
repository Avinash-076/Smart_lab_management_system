import requests

SERVER_URL = "http://127.0.0.1:8000/api"
SERVER_NAME = "SLMS"

def build_metric_payload(data: dict) ->dict:
    hardware = data.get("hardware") or {}
    network = data.get("network") or {}


    return {
        "cpu_usage": hardware.get("cpu_usage", 0),
        "ram_usage": hardware.get("ram_percent", 0),
        "disk_usage": hardware.get("disk_percent", 0),
        "network_sent": network.get("bytes_sent"),
        "network_received": network.get("bytes_received")
    }


def send_metrics(data: dict, access_token: str) -> dict:
    payload = build_metric_payload(data)

    response = requests.post(
        f"{SERVER_URL}/metrics",
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()