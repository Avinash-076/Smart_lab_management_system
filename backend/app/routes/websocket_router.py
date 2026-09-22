from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    HTTPException,
)
from sqlalchemy import select

from app.database import SessionLocal
from app.models.agent_credential import AgentCredential
from app.services import computer_service
from app.websocket.connection_manager import manager
from app.auth import decode_token


router = APIRouter()


@router.websocket("/ws/client/{computer_id}")
async def client_websocket(
    websocket: WebSocket,
    computer_id: int,
    token: str = Query(...),
):
    db = SessionLocal()

    try:
        payload = decode_token(token)

    except HTTPException:
        await websocket.close(code=4001)
        db.close()
        return

    if payload.get("type") != "agent":
        await websocket.close(code=4001)
        db.close()
        return

    agent_credential = db.scalar(
        select(AgentCredential).where(
            AgentCredential.agent_id == payload.get("sub"),
            AgentCredential.is_active == True,
        )
    )

    if (
        agent_credential is None
        or agent_credential.computer_id != computer_id
    ):
        await websocket.close(code=4001)
        db.close()
        return

    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        await websocket.close(code=4004)
        db.close()
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

    try:
        while True:
            message = await websocket.receive_text()

            # Every message from the client refreshes
            # its last-seen timestamp.
            manager.touch_client(computer_id)

            # The client currently sends "ping" every 20 seconds.
            # No response is required here.
            if message == "ping":
                continue

    except WebSocketDisconnect:
        manager.disconnect_client(computer_id)

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
        manager.disconnect_client(computer_id)

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


@router.websocket("/ws/dashboard")
async def dashboard_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return

    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect_dashboard(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

    except Exception:
        manager.disconnect_dashboard(websocket)