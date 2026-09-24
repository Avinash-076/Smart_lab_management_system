import os
import sys
import time

import keyring

from requests.exceptions import HTTPError

from config import (
    CLEAR_SCREEN,
    ENABLE_ISSUE_REPORTING,
    ENABLE_PROCESS_INFO,
    ENABLE_SOFTWARE_INFO,
    ENABLE_USAGE_INFO,
    EXPORT_JSON,
    MONITOR_INTERVAL,
    SERVER_NAME,
    SHOW_CONSOLE,
)

from core.collector import collect_all_data
from core.exporter import export_to_json
from core.logger import logger

from gui.enrollment_window import (
    show_enrollment_window,
)

from server.auth import get_access_token
from server.communication import (
    AgentWebSocketClient,
)
from server.enroll import is_enrolled

from server.sender import (
    send_issue,
    send_metrics,
    send_process_inventory,
    send_software_inventory,
    send_usage_sessions,
)


TOKEN_REFRESH_INTERVAL = 12 * 60


class TokenHolder:

    def __init__(
        self,
        token,
    ):
        self.token = token


# ==========================================
# Registration
# ==========================================

def ensure_registered():

    if is_enrolled():

        logger.info(
            "Existing SLMS registration found."
        )

        return

    logger.info(
        "No SLMS registration found."
    )

    logger.info(
        "Opening enrollment window."
    )

    show_enrollment_window()

    if not is_enrolled():

        raise RuntimeError(
            "SLMS enrollment was not completed."
        )

    logger.info(
        "Enrollment completed successfully."
    )


# ==========================================
# Computer ID
# ==========================================

def get_computer_id():

    value = keyring.get_password(
        SERVER_NAME,
        "computer_id",
    )

    if value is None:

        raise RuntimeError(
            "Computer ID not found in "
            "Windows Keyring."
        )

    return int(value)


# ==========================================
# Authentication
# ==========================================

def authenticate():

    logger.info(
        "Authenticating client agent..."
    )

    token = get_access_token()

    logger.info(
        "Authentication successful."
    )

    return token


# ==========================================
# Console Display
# ==========================================

def display_data(
    data,
):

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

        if isinstance(
            values,
            dict,
        ):

            for key, value in values.items():

                print(
                    f"{key:20}: {value}"
                )

        elif isinstance(
            values,
            list,
        ):

            print(
                f"Total items: {len(values)}"
            )


# ==========================================
# Metrics Upload
# ==========================================

def upload_metrics(
    data,
    token_holder,
):

    try:

        send_metrics(
            data,
            token_holder.token,
        )

        logger.info(
            "Metrics sent successfully."
        )

        return True

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

                send_metrics(
                    data,
                    token_holder.token,
                )

                logger.info(
                    "Metrics sent after "
                    "re-authentication."
                )

                return True

            except Exception as retry_error:

                logger.exception(
                    "Metric retry failed: "
                    f"{retry_error}"
                )

                return False

        logger.exception(
            f"Metric upload failed: {e}"
        )

        return False

    except Exception as e:

        logger.exception(
            f"Metric upload failed: {e}"
        )

        return False


# ==========================================
# Software Upload
# ==========================================

def upload_software(
    data,
    token_holder,
):

    if not ENABLE_SOFTWARE_INFO:

        return

    try:

        software = data.get(
            "software",
            [],
        )

        if not software:

            logger.info(
                "No software inventory found."
            )

            return

        send_software_inventory(
            data,
            token_holder.token,
        )

        logger.info(
            "Software inventory uploaded "
            f"successfully. "
            f"Items: {len(software)}"
        )

    except HTTPError as e:

        if (
            e.response is not None
            and e.response.status_code == 401
        ):

            logger.warning(
                "Software upload received "
                "401. Re-authenticating."
            )

            try:

                token_holder.token = (
                    authenticate()
                )

                send_software_inventory(
                    data,
                    token_holder.token,
                )

                logger.info(
                    "Software inventory uploaded "
                    "after re-authentication."
                )

            except Exception as retry_error:

                logger.exception(
                    "Software upload retry failed: "
                    f"{retry_error}"
                )

        else:

            logger.exception(
                f"Software inventory upload failed: {e}"
            )

    except Exception as e:

        logger.exception(
            f"Software inventory upload failed: {e}"
        )


# ==========================================
# Process Upload
# ==========================================

def upload_processes(
    data,
    token_holder,
):

    if not ENABLE_PROCESS_INFO:

        return

    try:

        processes = data.get(
            "processes",
            [],
        )

        if not processes:

            logger.info(
                "No running processes found."
            )

            return

        send_process_inventory(
            data,
            token_holder.token,
        )

        logger.info(
            "Process inventory uploaded "
            f"successfully. "
            f"Processes: {len(processes)}"
        )

    except HTTPError as e:

        if (
            e.response is not None
            and e.response.status_code == 401
        ):

            logger.warning(
                "Process upload received "
                "401. Re-authenticating."
            )

            try:

                token_holder.token = (
                    authenticate()
                )

                send_process_inventory(
                    data,
                    token_holder.token,
                )

                logger.info(
                    "Process inventory uploaded "
                    "after re-authentication."
                )

            except Exception as retry_error:

                logger.exception(
                    "Process upload retry failed: "
                    f"{retry_error}"
                )

        else:

            logger.exception(
                f"Process inventory upload failed: {e}"
            )

    except Exception as e:

        logger.exception(
            f"Process inventory upload failed: {e}"
        )


# ==========================================
# Usage Upload
# ==========================================

def upload_usage(
    data,
    token_holder,
):

    if not ENABLE_USAGE_INFO:

        return

    try:

        sessions = data.get(
            "usage",
            [],
        )

        if not sessions:

            logger.info(
                "No completed usage sessions found."
            )

            return

        send_usage_sessions(
            data,
            token_holder.token,
        )

        logger.info(
            "Usage history uploaded "
            f"successfully. "
            f"Sessions: {len(sessions)}"
        )

    except HTTPError as e:

        if (
            e.response is not None
            and e.response.status_code == 401
        ):

            logger.warning(
                "Usage upload received "
                "401. Re-authenticating."
            )

            try:

                token_holder.token = (
                    authenticate()
                )

                send_usage_sessions(
                    data,
                    token_holder.token,
                )

                logger.info(
                    "Usage history uploaded "
                    "after re-authentication."
                )

            except Exception as retry_error:

                logger.exception(
                    "Usage upload retry failed: "
                    f"{retry_error}"
                )

        else:

            logger.exception(
                f"Usage history upload failed: {e}"
            )

    except Exception as e:

        logger.exception(
            f"Usage history upload failed: {e}"
        )


# ==========================================
# Issue Reporting
# ==========================================

def upload_issues(
    data,
    token_holder,
):

    if not ENABLE_ISSUE_REPORTING:

        return

    issues = data.get(
        "issues",
        [],
    )

    if not issues:

        logger.info(
            "No new issues detected."
        )

        return

    for issue in issues:

        try:

            result = send_issue(
                issue,
                token_holder.token,
            )

            logger.warning(
                "Issue reported successfully: "
                f"{issue['title']}"
            )

            logger.info(
                f"Backend issue ID: "
                f"{result.get('id')}"
            )

        except HTTPError as e:

            if (
                e.response is not None
                and e.response.status_code == 401
            ):

                logger.warning(
                    "Issue upload received "
                    "401. Re-authenticating."
                )

                try:

                    token_holder.token = (
                        authenticate()
                    )

                    result = send_issue(
                        issue,
                        token_holder.token,
                    )

                    logger.warning(
                        "Issue reported after "
                        "re-authentication: "
                        f"{issue['title']}"
                    )

                    logger.info(
                        f"Backend issue ID: "
                        f"{result.get('id')}"
                    )

                except Exception as retry_error:

                    logger.exception(
                        "Issue retry failed: "
                        f"{retry_error}"
                    )

            else:

                logger.exception(
                    f"Issue upload failed: {e}"
                )

        except Exception as e:

            logger.exception(
                f"Issue upload failed: {e}"
            )


# ==========================================
# Main
# ==========================================

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

    # ------------------------------------------
    # WebSocket
    # ------------------------------------------

    ws_client = AgentWebSocketClient(
        computer_id=computer_id,
        get_token=lambda:
            token_holder.token,
    )

    ws_client.start()

    token_acquired_at = (
        time.monotonic()
    )

    try:

        while True:

            # --------------------------------------
            # Token Refresh
            # --------------------------------------

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

            # --------------------------------------
            # Clear Console
            # --------------------------------------

            if (
                CLEAR_SCREEN
                and SHOW_CONSOLE
                and not getattr(
                    sys,
                    "frozen",
                    False,
                )
            ):

                os.system(
                    "cls"
                )

            # --------------------------------------
            # Data Collection
            # --------------------------------------

            logger.info(
                "Collecting system information..."
            )

            data = collect_all_data()

            logger.info(
                "Data collection completed."
            )

            # --------------------------------------
            # Metrics
            # --------------------------------------

            upload_metrics(
                data,
                token_holder,
            )

            # --------------------------------------
            # Software
            # --------------------------------------

            upload_software(
                data,
                token_holder,
            )

            # --------------------------------------
            # Processes
            # --------------------------------------

            upload_processes(
                data,
                token_holder,
            )

            # --------------------------------------
            # Usage
            # --------------------------------------

            upload_usage(
                data,
                token_holder,
            )

            # --------------------------------------
            # Issues
            # --------------------------------------

            upload_issues(
                data,
                token_holder,
            )

            # --------------------------------------
            # JSON Export
            # --------------------------------------

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

            # --------------------------------------
            # Console
            # --------------------------------------

            if SHOW_CONSOLE:

                display_data(
                    data
                )

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