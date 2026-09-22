import os
import sys
import time

import keyring
from requests.exceptions import HTTPError

from config import (
    CLEAR_SCREEN,
    EXPORT_JSON,
    MONITOR_INTERVAL,
    SERVER_NAME,
    SHOW_CONSOLE,
)

from core.collector import collect_all_data
from core.exporter import export_to_json
from core.logger import logger

from server.auth import get_access_token
from server.enroll import is_enrolled
from gui.enrollment_window import show_enrollment_window
from server.sender import send_metrics
from server.communication import AgentWebSocketClient


TOKEN_REFRESH_INTERVAL = 12 * 60


class TokenHolder:

    def __init__(self, token):
        self.token = token


def ensure_registered():
    if is_enrolled():
        logger.info("Existing SLMS registration found.")
        return

    logger.info("No SLMS registration found.")
    logger.info("Opening enrollment window.")

    show_enrollment_window()

    if not is_enrolled():
        raise RuntimeError(
            "SLMS enrollment was not completed."
        )

    logger.info("Enrollment completed successfully.")

def get_computer_id():

    value = keyring.get_password(
        SERVER_NAME,
        "computer_id"
    )

    if value is None:

        raise RuntimeError(
            "Computer ID not found in Windows Keyring."
        )

    return int(value)


def authenticate():

    logger.info(
        "Authenticating client agent..."
    )

    token = get_access_token()

    logger.info(
        "Authentication successful."
    )

    return token


def display_data(data):

    print()
    print(
        "=" * 60
    )

    print(
        "SMART LAB MANAGEMENT SYSTEM"
    )

    print(
        "=" * 60
    )

    for section, values in data.items():

        print()
        print(
            section.upper()
        )

        print(
            "-" * 60
        )

        if values is None:

            print(
                "Unable to collect data."
            )

            continue

        if isinstance(values, dict):

            for key, value in values.items():

                print(
                    f"{key:20}: {value}"
                )

        elif isinstance(values, list):

            print(
                f"Total items: {len(values)}"
            )


def main():

    logger.info(
        "=" * 60
    )

    logger.info(
        "SLMS Client Agent Starting"
    )

    logger.info(
        "=" * 60
    )

    ensure_registered()

    access_token = authenticate()

    token_holder = TokenHolder(
        access_token
    )

    computer_id = get_computer_id()

    logger.info(
        f"Computer ID: {computer_id}"
    )

    ws_client = AgentWebSocketClient(
        computer_id=computer_id,
        get_token=lambda: token_holder.token,
    )

    ws_client.start()

    token_acquired_at = time.monotonic()

    try:

        while True:

            if (
                time.monotonic()
                - token_acquired_at
                > TOKEN_REFRESH_INTERVAL
            ):

                try:

                    logger.info(
                        "Refreshing access token..."
                    )

                    token_holder.token = (
                        authenticate()
                    )

                    token_acquired_at = (
                        time.monotonic()
                    )

                except Exception as e:

                    logger.exception(
                        f"Token refresh failed: {e}"
                    )

            if (
                CLEAR_SCREEN
                and SHOW_CONSOLE
                and not getattr(
                    sys,
                    "frozen",
                    False
                )
            ):

                os.system("cls")

            logger.info(
                "Collecting system information..."
            )

            data = collect_all_data()

            logger.info(
                "Data collection completed."
            )

            try:

                send_metrics(
                    data,
                    token_holder.token
                )

                logger.info(
                    "Metrics sent successfully."
                )

            except HTTPError as e:

                if (
                    e.response is not None
                    and e.response.status_code == 401
                ):

                    logger.warning(
                        "Access token expired. "
                        "Authenticating again."
                    )

                    try:

                        token_holder.token = (
                            authenticate()
                        )

                        token_acquired_at = (
                            time.monotonic()
                        )

                        send_metrics(
                            data,
                            token_holder.token
                        )

                        logger.info(
                            "Metrics sent after re-authentication."
                        )

                    except Exception as retry_error:

                        logger.exception(
                            "Retry failed: "
                            f"{retry_error}"
                        )

                else:

                    logger.exception(
                        f"Metric upload failed: {e}"
                    )

            except Exception as e:

                logger.exception(
                    f"Metric upload failed: {e}"
                )

            if EXPORT_JSON:

                try:

                    filepath = export_to_json(
                        data
                    )

                    logger.info(
                        f"JSON exported: {filepath}"
                    )

                except Exception as e:

                    logger.exception(
                        f"JSON export failed: {e}"
                    )

            if SHOW_CONSOLE:

                display_data(data)

                print()
                print(
                    f"Next scan in "
                    f"{MONITOR_INTERVAL} seconds..."
                )

            time.sleep(
                MONITOR_INTERVAL
            )

    except KeyboardInterrupt:

        logger.info(
            "Client stopped by user."
        )

    except Exception as e:

        logger.exception(
            f"Unexpected client error: {e}"
        )

    finally:

        ws_client.stop()

        logger.info(
            "SLMS Client Agent stopped."
        )


if __name__ == "__main__":
    main()