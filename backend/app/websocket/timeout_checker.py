import asyncio
from datetime import datetime, timezone

from app.database import SessionLocal
from app.services import computer_service
from app.websocket.connection_manager import manager


OFFLINE_TIMEOUT_SECONDS = 75
CHECK_INTERVAL_SECONDS = 20


async def run_offline_timeout_checker():
    while True:
        await asyncio.sleep(
            CHECK_INTERVAL_SECONDS
        )

        now = datetime.now(
            timezone.utc
        )

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
            > OFFLINE_TIMEOUT_SECONDS
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
                # Keep the background checker alive.
                pass

            finally:
                db.close()

            # Remove only the connection that was found
            # stale. A newer connection must remain online.
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