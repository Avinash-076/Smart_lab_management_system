import json
import threading
import time

import requests
import websocket

from config import API_BASE_URL, WS_BASE_URL
from core.logger import logger
from server.command_handler import execute_command


PING_INTERVAL_SECONDS = 20
RECONNECT_BASE_DELAY = 5
RECONNECT_MAX_DELAY = 60


class AgentWebSocketClient:

    def __init__(
        self,
        computer_id: int,
        get_token
    ):
        self.computer_id = computer_id
        self.get_token = get_token

        self._ws_app = None
        self._stop = False

    def start(self):
        thread = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name="SLMS-WebSocket"
        )

        thread.start()

    def stop(self):
        self._stop = True

        if self._ws_app is not None:
            try:
                self._ws_app.close()
            except Exception:
                pass

    def _run_forever(self):

        delay = RECONNECT_BASE_DELAY

        while not self._stop:

            try:

                token = self.get_token()

                url = (
                    f"{WS_BASE_URL}/"
                    f"{self.computer_id}"
                    f"?token={token}"
                )

                self._ws_app = websocket.WebSocketApp(
                    url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                logger.info(
                    "Connecting to SLMS WebSocket..."
                )

                self._ws_app.run_forever()

                delay = RECONNECT_BASE_DELAY

            except Exception as e:

                logger.exception(
                    f"WebSocket connection failed: {e}"
                )

            if self._stop:
                break

            logger.info(
                f"Reconnecting WebSocket in {delay} seconds..."
            )

            time.sleep(delay)

            delay = min(
                delay * 2,
                RECONNECT_MAX_DELAY
            )

    def _on_open(self, ws):

        logger.info(
            "WebSocket connected."
        )

        logger.info(
            "Client is now ONLINE."
        )

        threading.Thread(
            target=self._ping_loop,
            args=(ws,),
            daemon=True,
            name="SLMS-WebSocket-Ping"
        ).start()

    def _ping_loop(self, ws):

        while not self._stop:

            try:

                if (
                    ws.sock is None
                    or not ws.sock.connected
                ):
                    break

                ws.send("ping")

            except Exception as e:

                logger.warning(
                    f"WebSocket ping failed: {e}"
                )

                break

            time.sleep(
                PING_INTERVAL_SECONDS
            )

    def _on_message(
        self,
        ws,
        message
    ):

        logger.info(
            f"WebSocket message received: {message}"
        )

        try:
            data = json.loads(message)

        except (ValueError, TypeError):

            logger.warning(
                "Received invalid WebSocket JSON."
            )

            return

        if data.get("type") != "command":
            return

        command_id = data.get("command_id")
        command_type = data.get("command_type")
        payload = data.get("payload")

        if command_id is None:
            logger.warning(
                "Received command without command_id."
            )

            return

        success, result_message = execute_command(
            command_type,
            payload
        )

        self._send_command_result(
            command_id,
            success,
            result_message
        )

    def _send_command_result(
        self,
        command_id,
        success,
        message
    ):

        try:

            token = self.get_token()

            response = requests.post(
                f"{API_BASE_URL}"
                f"/api/commands/{command_id}/result",

                json={
                    "success": success,
                    "message": message,
                },

                headers={
                    "Authorization":
                        f"Bearer {token}"
                },

                timeout=10,
            )

            response.raise_for_status()

            logger.info(
                f"Command result sent: {command_id}"
            )

        except Exception as e:

            logger.exception(
                f"Failed to send command result: {e}"
            )

    def _on_error(
        self,
        ws,
        error
    ):

        logger.error(
            f"WebSocket error: {error}"
        )

    def _on_close(
        self,
        ws,
        close_status_code,
        close_msg
    ):

        logger.warning(
            "WebSocket closed "
            f"(code={close_status_code}, "
            f"message={close_msg})"
        )