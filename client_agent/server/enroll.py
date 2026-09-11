import requests
import keyring

from modules.system_info import get_system_info

SERVER_URL = "http://127.0.0.1:8000/api"
SERVICE_NAME = "SLMS"

def is_enrolled() -> bool:
    return keyring.get_password(SERVICE_NAME, "client_secret") is not None

def enroll():
    enrollment_key = input("Enter Enrollment Key: ").strip()

    sys_info = get_system_info()

    device = {
        "hostname": sys_info["computer_name"],
        "ip_address": sys_info["ip_address"],
        "mac_address": sys_info["mac_address"],
        "os_name": sys_info["operating_system"],
        "os_version": sys_info["os_version"]
    }

    response = requests.post(
        f"{SERVER_URL}/agent/register",
        json={
            "enrollment_key": enrollment_key,
            "device": device,
        },
        timeout = 10
    )

    response.raise_for_status()
    data = response.json()

    keyring.set_password(SERVICE_NAME, "agent_id", data["agent_id"])
    keyring.set_password(SERVICE_NAME, "client_secret", data["client_secret"])
    keyring.set_password(SERVICE_NAME, "computer_id", str(data["computer_id"]))

    print("Registration successful")