from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import select

from app.auth import decode_token
from app.database import SessionLocal
from app.models.agent_credential import AgentCredential
from app.services import (
    command_service,
    computer_service,
)
from app.websocket.connection_manager import manager


router = APIRouter()


@router.websocket(
    "/ws/client/{computer_id}"
)
async def client_websocket(
    websocket: WebSocket,
    computer_id: int,
    token: str = Query(...),
):
    db = SessionLocal()

    try:
        try:
            payload = decode_token(token)

        except HTTPException:
            await websocket.close(
                code=4001
            )
            return

        if payload.get("type") != "agent":
            await websocket.close(
                code=4001
            )
            return

        agent_credential = db.scalar(
            select(AgentCredential).where(
                AgentCredential.agent_id
                == payload.get("sub"),
                AgentCredential.is_active.is_(True),
            )
        )

        if (
            agent_credential is None
            or agent_credential.computer_id
            != computer_id
        ):
            await websocket.close(
                code=4001
            )
            return

        computer = (
            computer_service.get_computer_by_id(
                db,
                computer_id,
            )
        )

        if computer is None:
            await websocket.close(
                code=4004
            )
            return

        await manager.connect_client(
            computer_id,
            websocket,
        )

        computer_service.set_online(
            db,
            computer,
        )

        await manager.broadcast_to_dashboards(
            {
                "type": "status_update",
                "computer_id": computer_id,
                "status": "online",
            }
        )

        # Deliver commands that were created while
        # this computer was offline.
        try:
            await command_service.dispatch_pending_commands(
                db=db,
                computer_id=computer_id,
            )
        except Exception:
            # Do not terminate the WebSocket if pending
            # command delivery has a problem.
            pass

        while True:
            message = await websocket.receive_text()

            # Ignore messages from an old WebSocket that
            # has already been replaced.
            if not manager.is_active_connection(
                computer_id,
                websocket,
            ):
                break

            # Update in-memory heartbeat timestamp.
            last_seen = manager.touch_client(
                computer_id,
                websocket,
            )

            # Also persist heartbeat timestamp in SQLite.
            if last_seen is not None:
                computer_service.record_last_seen(
                    db,
                    computer,
                    last_seen,
                )

            if message == "ping":
                continue

    except WebSocketDisconnect:

        disconnected = manager.disconnect_client(
            computer_id,
            websocket,
        )

        # If this WebSocket was already replaced by a
        # newer connection, do not mark the computer offline.
        if not disconnected:
            return

        try:
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
            pass

    except Exception:

        disconnected = manager.disconnect_client(
            computer_id,
            websocket,
        )

        if not disconnected:
            return

        try:
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
            pass

    finally:
        db.close()


@router.websocket(
    "/ws/dashboard"
)
async def dashboard_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            await websocket.close(
                code=4001
            )
            return

    except Exception:
        await websocket.close(
            code=4001
        )
        return

    await manager.connect_dashboard(
        websocket
    )

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_dashboard(
            websocket
        )

    except Exception:
        manager.disconnect_dashboard(
            websocket
        )