import Icon from "../../../../components/ui/Icon";
import { REPORT_CATEGORIES } from "../../utils/reportUtils";
import "./ReportTypeSelector.css";

function ReportTypeSelector({ activeCategory, onSelectCategory, overview }) {
  const getBadgeValue = (cat) => {
    if (!overview) return null;
    const val = overview[cat.badgeKey];
    if (val === undefined || val === null) return null;
    return val;
  };

  return (
    <div className="report-type-selector-wrapper" role="tablist" aria-label="Report Categories">
      <div className="report-type-tabs">
        {REPORT_CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat.id;
          const badge = getBadgeValue(cat);

          return (
            <button
              key={cat.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`report-panel-${cat.id}`}
              id={`report-tab-${cat.id}`}
              className={`report-tab-btn ${isActive ? "report-tab-btn-active" : ""}`}
              onClick={() => onSelectCategory(cat.id)}
            >
              <span className="report-tab-icon">
                <Icon type={cat.icon} size={16} />
              </span>
              <span className="report-tab-label">{cat.label}</span>
              {badge !== null && (
                <span className={`report-tab-badge ${isActive ? "report-badge-active" : ""}`}>
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ReportTypeSelector;
