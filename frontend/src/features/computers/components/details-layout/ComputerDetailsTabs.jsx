import Icon from "../../../../components/ui/Icon";
import "./ComputerDetailsTabs.css";

const TABS = [
  { id: "hardware", label: "Hardware Info", icon: "chip" },
  { id: "matrix", label: "Matrix", icon: "grid" },
  { id: "history", label: "History", icon: "clock" },
  { id: "software", label: "Software", icon: "software" },
  { id: "processes", label: "Processes", icon: "details" },
  { id: "commands", label: "Remote Control", icon: "command" },
];

export default function ComputerDetailsTabs({ activeTab, onTabChange }) {
  return (
    <div className="computer-details-tabs-bar">
      <nav className="computer-details-tabs-nav" aria-label="Computer Details Navigation">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              id={`tab-${tab.id}`}
              className={`details-tab-btn ${isActive ? "active" : ""}`}
              onClick={() => onTabChange(tab.id)}
              aria-selected={isActive}
              role="tab"
            >
              <span className="details-tab-icon">
                <Icon type={tab.icon} size={18} />
              </span>
              <span className="details-tab-label">{tab.label}</span>
              {isActive && <span className="details-tab-indicator" />}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
