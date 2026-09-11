import time
from datetime import datetime

from process_filter import get_useful_applications


# ============================================================
# CONFIGURATION
# ============================================================

SCAN_INTERVAL = 2

# An application must remain absent for this amount of time
# before we confirm that it has actually closed.
CLOSE_CONFIRMATION_SECONDS = 5


# ============================================================
# HELPERS
# ============================================================

def create_app_map(applications):
    """
    Convert the application list into:

        {
            application_id: application
        }

    Multiple processes belonging to the same logical
    application become one entry.
    """

    app_map = {}

    for application in applications:

        application_id = application[
            "application_id"
        ]

        if application_id not in app_map:

            app_map[application_id] = application

        else:

            existing = app_map[
                application_id
            ]

            # Keep the earliest process start time.
            if (
                application["start_time"]
                < existing["start_time"]
            ):

                existing["start_time"] = (
                    application["start_time"]
                )

    return app_map


# ============================================================
# TRACKER
# ============================================================

def run_usage_tracker():

    # Applications confirmed active during the
    # previous scan.
    active_apps = {}

    # Applications that disappeared temporarily.
    #
    # This is INTERNAL state.
    # We never print these states.
    pending_closures = {}

    first_scan = True

    while True:

        # ----------------------------------------------------
        # GET CURRENT APPLICATIONS
        # ----------------------------------------------------

        current_list = (
            get_useful_applications()
        )

        current_apps = create_app_map(
            current_list
        )

        current_ids = set(
            current_apps.keys()
        )

        active_ids = set(
            active_apps.keys()
        )

        now = datetime.now()

        # ====================================================
        # FIRST SCAN
        # ====================================================

        if first_scan:

            for application in sorted(
                current_apps.values(),
                key=lambda item:
                    item["application_name"].lower()
            ):

                print(
                    "INITIAL:",
                    application[
                        "application_name"
                    ],
                    application[
                        "start_time"
                    ]
                )

            active_apps = current_apps

            first_scan = False

            time.sleep(
                SCAN_INTERVAL
            )

            continue

        # ====================================================
        # 1. FIND APPLICATIONS THAT RETURNED
        # ====================================================
        #
        # IMPORTANT:
        #
        # We determine returned applications BEFORE removing
        # them from pending_closures.
        #
        # This prevents a temporary disappearance from becoming
        # a new START event.
        #

        returned_ids = (
            set(pending_closures.keys())
            & current_ids
        )

        for application_id in returned_ids:

            pending_closures.pop(
                application_id,
                None
            )

        # ====================================================
        # 2. DETECT REAL STARTS
        # ====================================================
        #
        # New application:
        #
        #     current - previous
        #
        # But if it was previously pending closure and returned,
        # it is NOT a new START.
        #

        started_ids = (
            current_ids
            - active_ids
            - returned_ids
        )

        for application_id in sorted(
            started_ids,
            key=lambda app_id:
                current_apps[
                    app_id
                ][
                    "application_name"
                ].lower()
        ):

            application = current_apps[
                application_id
            ]

            print(
                "START:",
                application[
                    "application_name"
                ],
                application[
                    "start_time"
                ]
            )

        # ====================================================
        # 3. FIND NEWLY MISSING APPLICATIONS
        # ====================================================

        missing_ids = (
            active_ids
            - current_ids
        )

        for application_id in missing_ids:

            if (
                application_id
                not in pending_closures
            ):

                pending_closures[
                    application_id
                ] = {
                    "application": active_apps[
                        application_id
                    ],
                    "missing_since": now,
                }

        # ====================================================
        # 4. CONFIRM CLOSE
        # ====================================================
        #
        # An application must remain absent for the entire
        # confirmation period.
        #

        for application_id in list(
            pending_closures.keys()
        ):

            # Application returned.
            #
            # The return was already handled above, but this
            # guard makes the state machine safe.
            if application_id in current_ids:

                pending_closures.pop(
                    application_id,
                    None
                )

                continue

            pending = pending_closures[
                application_id
            ]

            missing_since = pending[
                "missing_since"
            ]

            elapsed_seconds = (
                now - missing_since
            ).total_seconds()

            if (
                elapsed_seconds
                >= CLOSE_CONFIRMATION_SECONDS
            ):

                application = pending[
                    "application"
                ]

                # IMPORTANT:
                # This is the actual detected close time,
                # not the application's original start time.
                close_time = now

                print(
                    "CLOSE:",
                    application[
                        "application_name"
                    ],
                    close_time
                )

                pending_closures.pop(
                    application_id,
                    None
                )

        # ====================================================
        # 5. UPDATE ACTIVE APPLICATIONS
        # ====================================================

        active_apps = current_apps

        # ====================================================
        # 6. WAIT
        # ====================================================

        time.sleep(
            SCAN_INTERVAL
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_usage_tracker()
