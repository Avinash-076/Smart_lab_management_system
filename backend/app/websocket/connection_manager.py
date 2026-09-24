from datetime import datetime, timezone

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.client_connections: dict[int, WebSocket] = {}
        self.client_last_seen: dict[int, datetime] = {}
        self.dashboard_connections: list[WebSocket] = []

    async def connect_client(
        self,
        computer_id: int,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

        old_connection = self.client_connections.get(
            computer_id
        )

        # Replace an older connection for the same computer.
        if (
            old_connection is not None
            and old_connection is not websocket
        ):
            try:
                await old_connection.close(
                    code=4002,
                    reason="Replaced by a new connection",
                )
            except Exception:
                pass

        self.client_connections[computer_id] = websocket

        self.client_last_seen[computer_id] = (
            datetime.now(timezone.utc)
        )

    def touch_client(
        self,
        computer_id: int,
        websocket: WebSocket | None = None,
    ) -> None:
        current_connection = (
            self.client_connections.get(computer_id)
        )

        if current_connection is None:
            return

        # If a specific WebSocket was supplied, make sure
        # it is still the active connection.
        if (
            websocket is not None
            and current_connection is not websocket
        ):
            return

        self.client_last_seen[computer_id] = (
            datetime.now(timezone.utc)
        )

    def is_active_connection(
        self,
        computer_id: int,
        websocket: WebSocket,
    ) -> bool:
        return (
            self.client_connections.get(computer_id)
            is websocket
        )

    def disconnect_client(
        self,
        computer_id: int,
        websocket: WebSocket | None = None,
    ) -> bool:
        current_connection = (
            self.client_connections.get(computer_id)
        )

        if current_connection is None:
            return False

        # Do not allow an old WebSocket to disconnect
        # a newer connection.
        if (
            websocket is not None
            and current_connection is not websocket
        ):
            return False

        self.client_connections.pop(
            computer_id,
            None,
        )

        self.client_last_seen.pop(
            computer_id,
            None,
        )

        return True

    async def connect_dashboard(
        self,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

        if websocket not in self.dashboard_connections:
            self.dashboard_connections.append(
                websocket
            )

    def disconnect_dashboard(
        self,
        websocket: WebSocket,
    ) -> None:
        if websocket in self.dashboard_connections:
            self.dashboard_connections.remove(
                websocket
            )

    async def broadcast_to_dashboards(
        self,
        message: dict,
    ) -> None:
        dead_connections: list[WebSocket] = []

        for connection in list(
            self.dashboard_connections
        ):
            try:
                await connection.send_json(
                    message
                )

            except Exception:
                dead_connections.append(
                    connection
                )

        for dead in dead_connections:
            self.disconnect_dashboard(
                dead
            )

    async def send_to_client(
        self,
        computer_id: int,
        message: dict,
    ) -> bool:
        connection = self.client_connections.get(
            computer_id
        )

        if connection is None:
            return False

        try:
            await connection.send_json(
                message
            )

            return True

        except Exception:
            self.disconnect_client(
                computer_id,
                connection,
            )

            return False


manager = ConnectionManager()