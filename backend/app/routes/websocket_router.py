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
    token: str | None = Query(default=None),
):
    # Authorization header is the target production architecture.
    # The '?token=' query parameter is supported temporarily for backward compatibility
    auth_header = websocket.headers.get("authorization")
    raw_token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        await websocket.close(
            code=4001
        )
        return

    try:
        payload = decode_token(raw_token)
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

    # Validate agent credentials and mark online in a short-lived session
    with SessionLocal() as db:
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

        computer_service.set_online(
            db,
            computer,
        )

        # Deliver commands that were created while this computer was offline
        try:
            await command_service.dispatch_pending_commands(
                db=db,
                computer_id=computer_id,
            )
        except Exception:
            pass

    # Database session is CLOSED before entering the event loop
    await manager.connect_client(
        computer_id,
        websocket,
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

            # Ignore messages from an old WebSocket that has already been replaced
            if not manager.is_active_connection(
                computer_id,
                websocket,
            ):
                break

            # Update in-memory heartbeat timestamp (zero DB contention)
            last_seen = manager.touch_client(
                computer_id,
                websocket,
            )

            # Persist heartbeat timestamp using a quick micro-session for telemetry payloads
            if last_seen is not None and message != "ping":
                try:
                    with SessionLocal() as db_touch:
                        comp = computer_service.get_computer_by_id(db_touch, computer_id)
                        if comp is not None:
                            computer_service.record_last_seen(
                                db_touch,
                                comp,
                                last_seen,
                            )
                except Exception:
                    pass

            if message == "ping":
                continue

    except WebSocketDisconnect:
        disconnected = manager.disconnect_client(
            computer_id,
            websocket,
        )

        # If this WebSocket was already replaced by a newer connection, do not mark offline
        if not disconnected:
            return

        try:
            with SessionLocal() as db_disc:
                comp = computer_service.get_computer_by_id(db_disc, computer_id)
                if comp is not None:
                    await computer_service.set_offline(
                        db_disc,
                        comp,
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
            with SessionLocal() as db_disc:
                comp = computer_service.get_computer_by_id(db_disc, computer_id)
                if comp is not None:
                    await computer_service.set_offline(
                        db_disc,
                        comp,
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


@router.websocket(
    "/ws/dashboard"
)
async def dashboard_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    auth_header = websocket.headers.get("authorization")
    raw_token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        await websocket.close(
            code=4001,
            reason="Missing token",
        )
        return

    try:
        payload = decode_token(raw_token)
    except Exception:
        await websocket.close(
            code=4001,
            reason="Invalid token",
        )
        return

    if payload.get("type") != "access":
        await websocket.close(
            code=4001,
            reason="Invalid token type",
        )
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(
            code=4001,
            reason="Invalid token payload",
        )
        return

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        await websocket.close(
            code=4001,
            reason="Invalid user identifier",
        )
        return

    from app.models.user import User
    from app.models.role_permission import RolePermission

    # Authenticate and check permissions using a quick short-lived session
    with SessionLocal() as db:
        user = db.get(User, user_id_int)
        if not user:
            await websocket.close(
                code=4001,
                reason="User not found",
            )
            return

        permission = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == user.role_id,
                RolePermission.action_code == "VIEW_COMPUTERS",
                RolePermission.allowed.is_(True),
            )
        )

        if not permission:
            await websocket.close(
                code=4003,
                reason="Forbidden: Missing VIEW_COMPUTERS permission",
            )
            return

    # Database session is CLOSED before entering the infinite loop!
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