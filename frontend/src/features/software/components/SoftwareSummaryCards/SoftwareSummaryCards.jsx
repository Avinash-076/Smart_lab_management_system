import Icon from "../../../../components/ui/Icon";
import "./SoftwareSummaryCards.css";

export default function SoftwareSummaryCards({
  summary,
  computersCount = 5,
  totalRecords = 217,
}) {
  const totalSoftware = summary?.total_software ?? totalRecords;
  const totalComputers = summary?.total_computers ?? (computersCount || 5);
  const computersWithSoftware = summary?.computers_with_software ?? totalComputers;
  const differentPublishers = summary?.different_publishers ?? 68;

  const mostCommonName = summary?.most_common_software?.name || "Google Chrome";
  const mostCommonCount =
    summary?.most_common_software?.count ?? (computersWithSoftware || 5);

  const computerPercentage =
    totalComputers > 0
      ? Math.round((computersWithSoftware / totalComputers) * 100)
      : 100;

  // SVG circular ring calculations
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset =
    circumference - (computerPercentage / 100) * circumference;

  return (
    <div className="software-summary-cards-grid">
      {/* 1. Total Software */}
      <div className="software-summary-card">
        <div className="software-summary-card-top">
          <div className="software-summary-icon blue">
            <Icon type="software" size={20} />
          </div>
          <div className="software-summary-mini-chart blue">
            <svg width="48" height="26" viewBox="0 0 48 26" fill="none">
              <rect x="2" y="16" width="4" height="10" rx="1.5" fill="#93c5fd" />
              <rect x="9" y="10" width="4" height="16" rx="1.5" fill="#93c5fd" />
              <rect x="16" y="6" width="4" height="20" rx="1.5" fill="#60a5fa" />
              <rect x="23" y="12" width="4" height="14" rx="1.5" fill="#93c5fd" />
              <rect x="30" y="4" width="4" height="22" rx="1.5" fill="#3b82f6" />
              <rect x="37" y="8" width="4" height="18" rx="1.5" fill="#60a5fa" />
              <rect x="44" y="14" width="4" height="12" rx="1.5" fill="#93c5fd" />
            </svg>
          </div>
        </div>
        <div className="software-summary-content">
          <span className="software-summary-label">Total Software</span>
          <div className="software-summary-value-row">
            <span className="software-summary-value">{totalSoftware}</span>
          </div>
          <span className="software-summary-subtext">Installed applications</span>
        </div>
      </div>

      {/* 2. Computers with Software */}
      <div className="software-summary-card">
        <div className="software-summary-card-top">
          <div className="software-summary-icon green">
            <Icon type="computer" size={20} />
          </div>
          <div className="software-summary-progress-ring">
            <svg width="44" height="44" viewBox="0 0 44 44">
              <circle
                cx="22"
                cy="22"
                r={radius}
                className="ring-bg"
                strokeWidth="3.5"
              />
              <circle
                cx="22"
                cy="22"
                r={radius}
                className="ring-fill green"
                strokeWidth="3.5"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                transform="rotate(-90 22 22)"
              />
              <text
                x="22"
                y="26"
                textAnchor="middle"
                className="ring-text"
                fontSize="10"
                fontWeight="700"
              >
                {`${computerPercentage}%`}
              </text>
            </svg>
          </div>
        </div>
        <div className="software-summary-content">
          <span className="software-summary-label">Computers with Software</span>
          <div className="software-summary-value-row">
            <span className="software-summary-value">
              {`${computersWithSoftware} / ${totalComputers}`}
            </span>
          </div>
          <span className="software-summary-subtext">All computers</span>
        </div>
      </div>

      {/* 3. Different Publishers */}
      <div className="software-summary-card">
        <div className="software-summary-card-top">
          <div className="software-summary-icon amber">
            <Icon type="details" size={20} />
          </div>
          <div className="software-summary-mini-chart purple">
            <svg width="48" height="26" viewBox="0 0 48 26" fill="none">
              <rect x="2" y="14" width="4" height="12" rx="1.5" fill="#ddd6fe" />
              <rect x="9" y="8" width="4" height="18" rx="1.5" fill="#c4b5fd" />
              <rect x="16" y="16" width="4" height="10" rx="1.5" fill="#ddd6fe" />
              <rect x="23" y="4" width="4" height="22" rx="1.5" fill="#a78bfa" />
              <rect x="30" y="10" width="4" height="16" rx="1.5" fill="#8b5cf6" />
              <rect x="37" y="14" width="4" height="12" rx="1.5" fill="#c4b5fd" />
              <rect x="44" y="6" width="4" height="20" rx="1.5" fill="#a78bfa" />
            </svg>
          </div>
        </div>
        <div className="software-summary-content">
          <span className="software-summary-label">Different Publishers</span>
          <div className="software-summary-value-row">
            <span className="software-summary-value">{differentPublishers}</span>
          </div>
          <span className="software-summary-subtext">Software publishers</span>
        </div>
      </div>

      {/* 4. Most Common Software */}
      <div className="software-summary-card">
        <div className="software-summary-card-top">
          <div className="software-summary-icon teal">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
          </div>
          <div className="software-summary-mini-chart teal">
            <svg width="48" height="26" viewBox="0 0 48 26" fill="none">
              <rect x="4" y="14" width="4" height="12" rx="1.5" fill="#a7f3d0" />
              <rect x="12" y="8" width="4" height="18" rx="1.5" fill="#6ee7b7" />
              <rect x="20" y="4" width="4" height="22" rx="1.5" fill="#10b981" />
              <rect x="28" y="10" width="4" height="16" rx="1.5" fill="#34d399" />
              <rect x="36" y="6" width="4" height="20" rx="1.5" fill="#10b981" />
            </svg>
          </div>
        </div>
        <div className="software-summary-content">
          <span className="software-summary-label">Most Common Software</span>
          <div className="software-summary-value-row">
            <span className="software-summary-value text-name" title={mostCommonName}>
              {mostCommonName}
            </span>
          </div>
          <span className="software-summary-subtext">
            {`Installed on ${mostCommonCount} computers`}
          </span>
        </div>
      </div>
    </div>
  );
}
