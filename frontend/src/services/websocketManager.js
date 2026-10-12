import { getAccessToken, isTokenExpired, refreshToken, clearTokens, registerLogoutHandler } from "./api";
import { getWsBaseUrl } from "./config";

/**
 * Registry of all active managed WebSocket instances.
 * Enables closing all real-time connections on logout or session invalidation.
 */
const activeSocketClients = new Set();

/**
 * Closes all active WebSocket connections across the application.
 * Called automatically during user logout or session cleanup.
 */
export function closeAllWebSockets() {
  for (const client of Array.from(activeSocketClients)) {
    try {
      client.close();
    } catch {
      // ignore individual socket close errors
    }
  }
  activeSocketClients.clear();
}

// Automatically close active sockets when logout occurs
registerLogoutHandler(closeAllWebSockets);

/**
 * Creates a managed WebSocket connection to /ws/dashboard with auto-reconnect,
 * token refresh, and lifecycle listeners.
 *
 * @param {Object} options
 * @param {Function} [options.onMessage] - Callback for incoming parsed JSON messages
 * @param {Function} [options.onStatusChange] - Callback for connection status changes
 * @param {number} [options.maxRetries=5] - Maximum reconnection attempts
 * @returns {{ close: Function }} Client controller
 */
export function createDashboardWebSocket({
  onMessage,
  onStatusChange,
  maxRetries = 5,
} = {}) {
  let socket = null;
  let isClosedExplicitly = false;
  let retryCount = 0;
  let retryTimer = null;

  const updateStatus = (status) => {
    if (onStatusChange) {
      onStatusChange(status); // 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
    }
  };

  const clientController = {
    close: () => {
      isClosedExplicitly = true;
      activeSocketClients.delete(clientController);
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
      if (socket) {
        try {
          socket.close(1000, "Client closed");
        } catch {
          // ignore
        }
        socket = null;
      }
      updateStatus("disconnected");
    },
  };

  activeSocketClients.add(clientController);

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

    if (isClosedExplicitly) return;

    updateStatus(retryCount > 0 ? "reconnecting" : "connecting");

    try {
      const baseUrl = getWsBaseUrl();
      const url = `${baseUrl}?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);

      socket.onopen = () => {
        if (isClosedExplicitly) {
          try {
            socket.close(1000, "Closed after disconnect");
          } catch {
            // ignore
          }
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

        // If closed due to auth rejection (4001: Unauthorized / 4003: Forbidden)
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

  // Start connection asynchronously
  connect();

  return clientController;
}
