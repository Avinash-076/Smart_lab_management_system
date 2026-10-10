import { getAccessToken, isTokenExpired, refreshToken, clearTokens } from "./api";

const WS_BASE_URL = "ws://127.0.0.1:8000/ws/dashboard";

/**
 * Creates a managed WebSocket connection to /ws/dashboard with auto-reconnect,
 * token refresh, and lifecycle listeners.
 */
export function createDashboardWebSocket({
  onMessage,
  onStatusChange,
  maxRetries = 5,
}) {
  let socket = null;
  let isClosedExplicitly = false;
  let retryCount = 0;
  let retryTimer = null;

  const updateStatus = (status) => {
    if (onStatusChange) {
      onStatusChange(status); // 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
    }
  };

  const connect = async () => {
    if (isClosedExplicitly) return;

    let token = getAccessToken();

    // Check if token is expired, try refresh if needed
    if (!token || isTokenExpired(token)) {
      try {
        token = await refreshToken();
      } catch {
        clearTokens();
        updateStatus("disconnected");
        return;
      }
    }

    updateStatus(retryCount > 0 ? "reconnecting" : "connecting");

    try {
      const url = `${WS_BASE_URL}?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);

      socket.onopen = () => {
        if (isClosedExplicitly) {
          socket.close();
          return;
        }
        retryCount = 0;
        updateStatus("connected");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && onMessage) {
            onMessage(data);
          }
        } catch (parseErr) {
          console.warn("Received non-JSON WebSocket message:", parseErr);
        }
      };

      socket.onerror = (err) => {
        console.warn("WebSocket connection error:", err);
      };

      socket.onclose = (event) => {
        socket = null;
        if (isClosedExplicitly) {
          updateStatus("disconnected");
          return;
        }

        // If closed due to auth rejection (4001 / 4003)
        if (event.code === 4001 || event.code === 4003) {
          updateStatus("disconnected");
          return;
        }

        // Bounded exponential backoff retry
        if (retryCount < maxRetries) {
          const delay = Math.min(1000 * Math.pow(1.5, retryCount), 10000);
          retryCount += 1;
          updateStatus("reconnecting");
          retryTimer = setTimeout(connect, delay);
        } else {
          updateStatus("disconnected");
        }
      };
    } catch (connErr) {
      console.error("Failed to establish WebSocket connection:", connErr);
      updateStatus("disconnected");
    }
  };

  // Start connection
  connect();

  return {
    close: () => {
      isClosedExplicitly = true;
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      if (socket) {
        try {
          socket.close();
        } catch {
          // ignore
        }
        socket = null;
      }
      updateStatus("disconnected");
    },
  };
}
