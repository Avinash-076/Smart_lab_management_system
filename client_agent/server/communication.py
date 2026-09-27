import json
import threading
import time

import requests
import websocket

from config import get_api_base_url, get_ws_base_url
from core.logger import logger
from core.security import (
    build_websocket_endpoint,
    build_websocket_headers,
    create_secure_session,
    get_ca_bundle_path,
)
from server.command_handler import execute_command


PING_INTERVAL_SECONDS = 20

RECONNECT_BASE_DELAY = 5
RECONNECT_MAX_DELAY = 60


class AgentWebSocketClient:

    def __init__(
        self,
        computer_id: int,
        get_token,
        outbox=None,
    ):
        self.computer_id = computer_id
        self.get_token = get_token
        self.outbox = outbox

        self._ws_app = None
        self._stop = False
        self._thread = None

    # ==========================================
    # Start
    # ==========================================

    def start(self):
        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            return

        self._stop = False

        self._thread = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name="SLMS-WebSocket",
        )

        self._thread.start()

    # ==========================================
    # Stop
    # ==========================================

    def stop(self):

        self._stop = True

        if self._ws_app is not None:

            try:
                self._ws_app.close()

            except Exception:
                pass

    # ==========================================
    # WebSocket Loop
    # ==========================================

    def _run_forever(self):

        delay = RECONNECT_BASE_DELAY

        while not self._stop:

            try:

                token = self.get_token()
                ws_base = get_ws_base_url()
                url = build_websocket_endpoint(ws_base, self.computer_id)
                headers = build_websocket_headers(token)

                sslopt = {}
                ca_bundle = get_ca_bundle_path()
                if ca_bundle:
                    sslopt["ca_certs"] = ca_bundle

                logger.info(
                    f"Connecting to SLMS WebSocket at {url}..."
                )

                self._ws_app = websocket.WebSocketApp(
                    url,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                self._ws_app.run_forever(
                    ping_interval=None,
                    ping_timeout=None,
                    sslopt=sslopt if sslopt else None,
                )

                if self._stop:
                    break

                logger.warning(
                    "WebSocket connection ended."
                )

            except Exception as error:

                logger.exception(
                    "WebSocket connection failed: "
                    f"{error}"
                )

            if self._stop:
                break

            logger.info(
                "Reconnecting WebSocket in "
                f"{delay} seconds..."
            )

            time.sleep(delay)

            delay = min(
                delay * 2,
                RECONNECT_MAX_DELAY,
            )

        logger.info(
            "WebSocket worker stopped."
        )

    # ==========================================
    # Connection Open
    # ==========================================

    def _on_open(self, ws):

        logger.info(
            "WebSocket connected."
        )

        logger.info(
            "Client is now ONLINE."
        )

        # Reset reconnect delay after a genuinely
        # successful connection.
        #
        # The outer loop will continue with its current
        # delay, so this is intentionally not used to
        # force rapid reconnects.
        threading.Thread(
            target=self._ping_loop,
            args=(ws,),
            daemon=True,
            name="SLMS-WebSocket-Ping",
        ).start()

    # ==========================================
    # Heartbeat
    # ==========================================

    def _ping_loop(self, ws):

        while not self._stop:

            try:

                if (
                    ws.sock is None
                    or not ws.sock.connected
                ):
                    break

                ws.send("ping")

                logger.debug(
                    "WebSocket heartbeat sent."
                )

            except Exception as error:

                logger.warning(
                    "WebSocket ping failed: "
                    f"{error}"
                )

                break

            time.sleep(
                PING_INTERVAL_SECONDS
            )

    # ==========================================
    # Incoming Message
    # ==========================================

    def _on_message(
        self,
        ws,
        message,
    ):

        logger.info(
            f"WebSocket message received: {message}"
        )

        try:

            data = json.loads(message)

        except (
            ValueError,
            TypeError,
        ):

            logger.warning(
                "Received invalid WebSocket JSON."
            )

            return

        if data.get("type") != "command":
            return

        command_id = data.get(
            "command_id"
        )

        command_type = data.get(
            "command_type"
        )

        payload = data.get(
            "payload"
        )

        if command_id is None:

            logger.warning(
                "Received command without command_id."
            )

            return

        if not command_type:

            logger.warning(
                "Received command without command_type."
            )

            return

        success, result_message = execute_command(
            command_type,
            payload,
        )

        if self.outbox is not None:
            try:
                from core.outbox.models import OutboxPriority
                self.outbox.enqueue(
                    event_type="command_result",
                    payload={
                        "command_id": command_id,
                        "success": success,
                        "message": result_message,
                    },
                    idempotency_key=f"cmd_result_{command_id}",
                    priority=OutboxPriority.COMMAND,
                    max_attempts=10,
                )
                logger.info(
                    f"Command result enqueued to durable outbox: {command_id}"
                )
            except Exception as outbox_error:
                logger.exception(
                    f"Failed to enqueue command result to outbox: {outbox_error}"
                )
                self._send_command_result(
                    command_id,
                    success,
                    result_message,
                )
        else:
            self._send_command_result(
                command_id,
                success,
                result_message,
            )

    # ==========================================
    # Command Result
    # ==========================================

    def _send_command_result(
        self,
        command_id,
        success,
        message,
    ):

        try:

            token = self.get_token()
            api_url = get_api_base_url()
            session = create_secure_session()

            response = session.post(
                f"{api_url}/api/commands/{command_id}/result",
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

        except requests.HTTPError as error:

            logger.exception(
                "Command result request failed: "
                f"{error}"
            )

        except Exception as error:

            logger.exception(
                "Failed to send command result: "
                f"{error}"
            )

    # ==========================================
    # WebSocket Error
    # ==========================================

    def _on_error(
        self,
        ws,
        error,
    ):

        logger.error(
            f"WebSocket error: {error}"
        )

    # ==========================================
    # WebSocket Close
    # ==========================================

    def _on_close(
        self,
        ws,
        close_status_code,
        close_msg,
    ):

        logger.warning(
            "WebSocket closed "
            f"(code={close_status_code}, "
            f"message={close_msg})"
        )