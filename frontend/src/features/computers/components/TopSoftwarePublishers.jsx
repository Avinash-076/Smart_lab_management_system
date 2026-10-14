import "./TopSoftwarePublishers.css";

function PublisherBrandIcon({ publisher = "" }) {
  const pubLower = (publisher || "").toLowerCase();

  if (pubLower.includes("microsoft")) {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="2" width="9.5" height="9.5" fill="#f25022" />
        <rect x="12.5" y="2" width="9.5" height="9.5" fill="#7fba00" />
        <rect x="2" y="12.5" width="9.5" height="9.5" fill="#00a4ef" />
        <rect x="12.5" y="12.5" width="9.5" height="9.5" fill="#ffb900" />
      </svg>
    );
  }

  if (pubLower.includes("google")) {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
      </svg>
    );
  }

  if (pubLower.includes("mozilla")) {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="#ff7139" />
        <path d="M12 4C7.58 4 4 7.58 4 12c0 1.25.29 2.43.8 3.48.55-.83 1.4-1.48 2.4-1.78.3-.09.7-.15 1.05-.15.4 0 .75.05 1.1.15 1.25.35 2.15 1.4 2.25 2.7.05.6-.1 1.15-.4 1.65.65.6 1.45.95 2.35.95 1.95 0 3.55-1.6 3.55-3.55 0-1.8-1.35-3.3-3.1-3.5-.4-.05-.8-.05-1.2.05-1.2.3-2.15 1.2-2.55 2.35-.15.45-.2.95-.15 1.45-.55-.65-.85-1.5-.85-2.4 0-1.95 1.35-3.6 3.2-3.95.5-.1 1.05-.1 1.55.05 1.8.45 3.1 2.05 3.1 3.95 0 2.2-1.8 4-4 4-1.2 0-2.3-.5-3-1.3.1.5.35.95.7 1.3C8.4 21.2 10.1 22 12 22c5.5 0 10-4.5 10-10S17.5 4 12 4z" fill="#ffffff" />
      </svg>
    );
  }

  if (pubLower.includes("intel")) {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="5" width="20" height="14" rx="3" fill="#0068b5" />
        <text x="12" y="15" textAnchor="middle" fill="#ffffff" fontSize="9" fontWeight="bold" fontFamily="sans-serif">
          intel
        </text>
      </svg>
    );
  }

  if (pubLower.includes("realtek")) {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="4" fill="#005596" />
        <circle cx="12" cy="12" r="5" stroke="#ffffff" strokeWidth="2" fill="none" />
        <path d="M8 8l8 8" stroke="#ffffff" strokeWidth="2" />
      </svg>
    );
  }

  if (pubLower === "others") {
    return (
      <svg className="publisher-brand-svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="4" fill="#0962df" />
        <circle cx="8.5" cy="8.5" r="1.5" fill="#ffffff" />
        <circle cx="15.5" cy="8.5" r="1.5" fill="#ffffff" />
        <circle cx="8.5" cy="15.5" r="1.5" fill="#ffffff" />
        <circle cx="15.5" cy="15.5" r="1.5" fill="#ffffff" />
      </svg>
    );
  }

  // Fallback organization / publisher icon
  return (
    <div className="publisher-generic-icon">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    </div>
  );
}

export default function TopSoftwarePublishers({
  publishers = [],
  totalApplications = 0,
  loading = false,
}) {
  const maxCount = Math.max(
    1,
    ...publishers.map((p) => p.count || 0)
  );

  return (
    <div className="software-analytics-card software-publishers-card">
      <div className="analytics-card-header">
        <div className="analytics-card-title-group">
          <div className="analytics-icon-badge">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h3 className="analytics-card-title">Top Publishers</h3>
        </div>
      </div>

      <div className="software-publishers-list">
        {publishers.length === 0 ? (
          <div className="software-publishers-empty">
            {loading ? "Calculating publisher statistics..." : "No publisher records available"}
          </div>
        ) : (
          publishers.map((item) => {
            const percentage = totalApplications > 0
              ? (item.percentage ?? Math.round((item.count / totalApplications) * 100))
              : 0;

            // Bar fill proportion relative to max publisher or total
            const barWidthPercent = Math.min(
              100,
              Math.max(8, Math.round((item.count / maxCount) * 100))
            );

            return (
              <div key={item.publisher} className="publisher-row">
                {/* Brand Icon + Name */}
                <div className="publisher-identity">
                  <div className="publisher-icon-box">
                    <PublisherBrandIcon publisher={item.publisher} />
                  </div>
                  <span className="publisher-name" title={item.publisher}>
                    {item.publisher}
                  </span>
                </div>

                {/* Horizontal Progress Bar */}
                <div className="publisher-bar-track">
                  <div
                    className="publisher-bar-fill"
                    style={{ width: `${barWidthPercent}%` }}
                  />
                </div>

                {/* Count and Percentage on right */}
                <div className="publisher-stats">
                  <span className="publisher-count">{item.count}</span>
                  <span className="publisher-pct">({percentage}%)</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
