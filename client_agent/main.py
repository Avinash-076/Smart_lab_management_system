import os
import sys
import time
import keyring

from core.collector import collect_all_data
from core.exporter import export_to_json
from core.logger import logger
from startup import add_to_startup

from config import (
    MONITOR_INTERVAL,
    EXPORT_JSON,
    CLEAR_SCREEN,
    SHOW_CONSOLE,
    SHOW_SOFTWARE_LIST,
    SHOW_PROCESS_LIST,
)

from server.sender import send_metrics
from requests.exceptions import HTTPError

from server.enroll import is_enrolled, enroll
from server.auth import get_access_token

from server.communication import AgentWebSocketClient

TOKEN_REFRESH_INTERVAL = 12 * 60

SERVER_NAME = "SLMS"

class TokenHolder:
    def __init__(self,token):
        self.token = token

def display_data(data):
    print("\n========== SMART LAB MANAGEMENT SYSTEM ==========\n")

    for section, values in data.items():

        print(f"\n{section.upper()}")
        print("-" * 70)

        if values is None:
            print("Unable to collect data.")
            continue

        # Dictionary Sections
        if isinstance(values, dict):

            for key, value in values.items():
                print(f"{key:20}: {value}")

        # List Sections
        elif isinstance(values, list):

            print(f"Total Items : {len(values)}\n")

            # ---------------- Software ----------------
            from itertools import groupby

            def group_by_first_word(software_list):
                grouped = {}
                for app in software_list:
                    name = app.get("name", "Unknown")
                    first_word = name.split(" ")[0] if name else "Unknown"
                    grouped.setdefault(first_word, []).append(app)
                return dict(sorted(grouped.items(), key=lambda x: x[0].lower()))



                        # ---------------- Software ----------------
            if section == "software":

                if SHOW_SOFTWARE_LIST:

                    grouped = group_by_first_word(values)

                    for group_name, apps in grouped.items():
                        print(f"\n[{group_name}]  ({len(apps)})")

                        for app in apps:
                            print(f"    {app.get('name', 'Unknown'):<55} {app.get('version', 'Unknown')}")

                    print("-" * 70)

                else:
                    print("Software list hidden.")
            # ---------------- Processes ----------------
            elif section == "processes":

                if SHOW_PROCESS_LIST:

                    print(
                        f"{'PID':<8}"
                        f"{'Name':<30}"
                        f"{'CPU %':>8}"
                        f"{'RAM %':>8}"
                        f"{'Status':>12}"
                    )

                    print("-" * 70)

                    for process in values:

                        print(
                            f"{process.get('pid', ''):<8}"
                            f"{process.get('name', '')[:28]:<30}"
                            f"{process.get('cpu_percent', 0):>8.1f}"
                            f"{process.get('memory_percent', 0):>8.2f}"
                            f"{process.get('status', ''):>12}"
                        )

                else:
                    print("Process list hidden.")

def ensure_registered():
    if is_enrolled():
        return

    logger.info("No local credentials found. Starting enrollment...")

    try:
        enroll()
        logger.info("Enrollment successful")

    except Exception as e:
        logger.exception(f"Enrollment failed: {e}")
        print(f"\nEnrollment failed: {e}")
        sys.exit(1)

def refresh_access_token():
    try:
        token = get_access_token()
        logger.info("Access token acquired.")
        return token

    except Exception as e:
        logger.exception(f"Authentication failed: {e}")
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)

def main():

    logger.info("=" * 60)
    logger.info("SLMS Client Agent Started")

    # Register application in Startup folder (Only when running as EXE)
  #  if getattr(sys, "frozen", False):

      #  if add_to_startup(sys.executable):
           # logger.info("Startup registration successful.")
        #else:
         #   logger.warning("Startup registration failed.")

    ensure_registered()

    access_token = refresh_access_token()
    token_acquired_at = time.monotonic()

    token_holder = TokenHolder(access_token)
    password = keyring.get_password(SERVER_NAME, "computer_id")
    if password is None:
        logger.error("Computer ID not found in keyring. Ensure enrollment has stored the ID.")
        sys.exit(1)
    computer_id = int(password)

    ws_client = AgentWebSocketClient(
        computer_id=computer_id,
        get_token=lambda: token_holder.token,
    )

    ws_client.start()

    try:

        while True:

            if CLEAR_SCREEN and not getattr(sys, "frozen", False):
                 os.system("cls")


            if (time.monotonic() - token_acquired_at) > TOKEN_REFRESH_INTERVAL:
                access_token = refresh_access_token()
                token_holder.token = access_token
                token_acquired_at = time.monotonic()
            

            logger.info("Collecting system information...")

            data = collect_all_data()

            logger.info("Data collection completed.")

            try:
                send_metrics(data, access_token)
                logger.info("Metric sent to server.")

            except HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    logger.warning("Token expired mid-cycle, refreshing...")
                    access_token = refresh_access_token()
                    token_acquired_at = time.monotonic()

                    try: 
                        send_metrics(data, access_token)

                    except Exception as e2:
                        logger.exception(f"Retry after refresh failed: {e2}")

                else:
                    logger.exception(f"Failed to send metrics: {e}")

            except Exception as e:
                logger.exception(f"Failed to send metrics: {e}")

            if EXPORT_JSON:

                filepath = export_to_json(data)

                logger.info(f"JSON exported: {filepath}")

            if SHOW_CONSOLE:

                display_data(data)

                print(f"\nNext Scan in {MONITOR_INTERVAL} seconds...")
                print("=" * 70)

            logger.info("Monitoring cycle completed.")

            time.sleep(MONITOR_INTERVAL)

    except KeyboardInterrupt:
        ws_client.stop()
        logger.info("Client stopped by user.")
        print("\nMonitoring stopped.")

    except Exception as e:

        logger.exception(f"Unexpected Error: {e}")
        print(f"\nUnexpected Error: {e}")


if __name__ == "__main__":
    main()