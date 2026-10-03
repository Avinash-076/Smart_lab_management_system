import { useState, useEffect, useRef } from "react";
import { createDashboardWebSocket } from "../services/websocket";

export function useComputerWebSocket(computerId, { onMetricUpdate, onStatusUpdate }) {
  const [wsStatus, setWsStatus] = useState(
    computerId ? "connecting" : "disconnected"
  ); // 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

  const onMetricUpdateRef = useRef(onMetricUpdate);
  const onStatusUpdateRef = useRef(onStatusUpdate);

  useEffect(() => {
    onMetricUpdateRef.current = onMetricUpdate;
  }, [onMetricUpdate]);

  useEffect(() => {
    onStatusUpdateRef.current = onStatusUpdate;
  }, [onStatusUpdate]);

  useEffect(() => {
    if (!computerId) {
      return;
    }

    const wsClient = createDashboardWebSocket({
      onStatusChange: (status) => {
        setWsStatus(status);
      },
      onMessage: (message) => {
        if (!message || message.computer_id !== computerId) {
          return;
        }

        if (message.type === "metric_update" && onMetricUpdateRef.current) {
          onMetricUpdateRef.current(message);
        } else if (message.type === "status_update" && onStatusUpdateRef.current) {
          onStatusUpdateRef.current(message);
        }
      },
    });

    return () => {
      wsClient.close();
    };
  }, [computerId]);

  return { wsStatus };
}
