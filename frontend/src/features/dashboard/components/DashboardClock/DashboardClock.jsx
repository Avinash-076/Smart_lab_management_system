import { useState, useEffect } from "react";
import "./DashboardClock.css";

export default function DashboardClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const timeStr = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });

  const dateStr = now.toLocaleDateString([], {
    day: "numeric",
    month: "short",
    year: "numeric",
    weekday: "long",
  });

  return (
    <div className="dashboard-clock-card" data-testid="dashboard-clock">
      <div className="dashboard-clock-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      </div>
      <div className="dashboard-clock-info">
        <span className="dashboard-clock-time">{timeStr}</span>
        <span className="dashboard-clock-date">{dateStr}</span>
      </div>
    </div>
  );
}
