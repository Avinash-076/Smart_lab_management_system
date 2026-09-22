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

        self.client_connections[computer_id] = websocket
        self.client_last_seen[computer_id] = datetime.now(
            timezone.utc
        )

    def touch_client(
        self,
        computer_id: int,
    ) -> None:
        if computer_id in self.client_connections:
            self.client_last_seen[computer_id] = datetime.now(
                timezone.utc
            )

    def disconnect_client(
        self,
        computer_id: int,
    ) -> None:
        self.client_connections.pop(
            computer_id,
            None,
        )

        self.client_last_seen.pop(
            computer_id,
            None,
        )

    async def connect_dashboard(
        self,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()

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
        dead_connections = []

        for connection in self.dashboard_connections:
            try:
                await connection.send_json(message)

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
            # The connection exists in the manager,
            # but the actual WebSocket is no longer usable.
            self.disconnect_client(
                computer_id
            )

            return False


manager = ConnectionManager()