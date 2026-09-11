import asyncio
from datetime import datetime, timezone

from app.database import SessionLocal
from app.services import computer_service
from app.websocket.connection_manager import manager


OFFLINE_TIMEOUT_SECONDS = 75
CHECK_INTERVAL_SECONDS = 20


async def run_offline_timeout_checker():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        now = datetime.now(timezone.utc)
        stale_computer_ids = [
            computer_id
            for computer_id, last_seen in list(manager.client_last_seen.items())
            if (now - last_seen).total_seconds() > OFFLINE_TIMEOUT_SECONDS
        ]

        for computer_id in stale_computer_ids:

            db = SessionLocal()
            try:
                computer = computer_service.get_computer_by_id(db, computer_id)
                if computer is not None:
                    computer_service.set_offline(db, computer)
            finally:
                db.close()

            # 2. Remove from manager so touch_client / new connections are clean.
            manager.disconnect_client(computer_id)

            # 3. Best-effort close — may fail if the TCP connection is already gone.
            websocket = manager.client_connections.get(computer_id)
            if websocket is not None:
                try:
                    await websocket.close(code=4000)
                except Exception:
                    pass