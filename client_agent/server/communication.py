import threading
import time
import json
import requests
import websocket

from core.logger import logger
from config import WS_BASE_URL
from server.command_handler import execute_command

PING_INTERVAL_SECONDS = 20
RECONNECT_BASE_DELAY = 5
RECONNECT_MAX_DELAY = 60

SERVER_URL = "http://127.0.0.1:8000/api"

class AgentWebSocketClient:
    def __init__(self, computer_id: int, get_token):
        """
        get_token: a zero-arg callable that returns the CURRENT agent access token.
        We use a callable (not a fixed string) so that if the token gets refreshed
        while we're reconnecting, we pick up the new one automatically.
        """
        self.computer_id = computer_id
        self.get_token = get_token
        self._ws_app = None
        self._stop = False

    def start(self):
        threading.Thread(target=self._run_forever, daemon=True).start()

    def stop(self):
        self._stop = True
        if self._ws_app is not None:
            self._ws_app.close()

    def _run_forever(self):
        delay = RECONNECT_BASE_DELAY
        while not self._stop:
            try:
                token = self.get_token()
                url = f"{WS_BASE_URL}/{self.computer_id}?token={token}"

                self._ws_app = websocket.WebSocketApp(
                    url,
                    on_open= self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )

                logger.info("Connecting Websocket to server")
                self._ws_app.run_forever()
                delay = RECONNECT_BASE_DELAY

            except Exception as e:
                logger.exception(f"WebSocket connection failed: {e}")

            if self._stop:
                break

            logger.info(f"Reconnecting Websocket in {delay}s...")
            time.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)

    def _on_open(self, ws):
        logger.info("WebSocket connected - client is now ONLINE")
        threading.Thread(target=self._ping_loop, args=(ws,), daemon=True).start()

    def _ping_loop(self, ws):
        while not self._stop and ws.sock and ws.sock.connected:
            try:
                ws.send("ping")
            except Exception:
                break
            time.sleep(PING_INTERVAL_SECONDS)

    def _on_message(self, ws, message):
        logger.info(f"WebSocket message received: {message}")

        try:
            data = json.loads(message)
        
        except ValueError:
            return

        if data.get("type") != "command":
            return

        command_id = data.get("command_id")

        success, result_message = execute_command(data.get("command_type"), data.get("payload"))

        try: 
            requests.post(
                f"{SERVER_URL}/commands/{command_id}/result",
                json={
                    "success": success,
                    "message": result_message,
                },
                headers={
                    "Authorization": f"Bearer {self.get_token()}",
                },
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Failed to send command result: {e}")

    def _on_error(self, ws, error):
        logger.error(f"Websocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.warning(f"websocket closed (code={close_status_code}): {close_msg}")