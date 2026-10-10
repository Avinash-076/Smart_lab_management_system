import asyncio
from datetime import datetime, timezone

from app.database import SessionLocal
from app.services import computer_service
from app.websocket.connection_manager import manager


# The client sends periodic heartbeats.
# We allow 2.5 missed heartbeats before considering the client offline.
DEFAULT_OFFLINE_TIMEOUT_SECONDS = 75

# Check for stale connections every 20 seconds.
CHECK_INTERVAL_SECONDS = 20


async def run_offline_timeout_checker():
    while True:
        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )

        now = datetime.now(timezone.utc)

        # Dynamic offline timeout calculation from persistent settings
        from app.services.setting_service import get_setting_value
        try:
            with SessionLocal() as db_check:
                heartbeat_sec = get_setting_value(db_check, "heartbeat_interval", 30)
                offline_timeout = max(15, int(heartbeat_sec * 2.5))
        except Exception:
            offline_timeout = DEFAULT_OFFLINE_TIMEOUT_SECONDS

        stale_computers = [
            (
                computer_id,
                last_seen,
            )
            for computer_id, last_seen
            in list(
                manager.client_last_seen.items()
            )
            if (
                now - last_seen
            ).total_seconds()
            > offline_timeout
        ]

        for computer_id, last_seen in stale_computers:

            websocket = (
                manager.client_connections.get(
                    computer_id
                )
            )

            # The connection may have refreshed while
            # this list was being processed.
            current_last_seen = (
                manager.client_last_seen.get(
                    computer_id
                )
            )

            if (
                current_last_seen is None
                or current_last_seen != last_seen
            ):
                continue

            db = SessionLocal()

            try:
                computer = (
                    computer_service.get_computer_by_id(
                        db,
                        computer_id,
                    )
                )

                if computer is None:
                    manager.disconnect_client(
                        computer_id,
                        websocket,
                    )
                    continue

                await computer_service.set_offline(
                    db,
                    computer,
                )

                await manager.broadcast_to_dashboards(
                    {
                        "type": "status_update",
                        "computer_id": computer_id,
                        "status": "offline",
                    }
                )

            except Exception:
                # Keep the background checker alive even
                # if one computer causes a database error.
                pass

            finally:
                db.close()

            # Remove only the stale connection.
            #
            # If a newer connection has appeared meanwhile,
            # disconnect_client() will refuse to remove it.
            manager.disconnect_client(
                computer_id,
                websocket,
            )

            if websocket is not None:
                try:
                    await websocket.close(
                        code=4000,
                        reason="Heartbeat timeout",
                    )
                except Exception:
                    pass