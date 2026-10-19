import Icon from "../../../../components/ui/Icon";
import { SETTING_CATEGORIES } from "../../utils/settingUtils";
import "./SettingsTabs.css";

function SettingsTabs({ activeTab, onSelectTab, categoryDirtyCounts = {} }) {
  return (
    <div className="settings-tabs-container" role="tablist" aria-label="Settings Categories">
      {SETTING_CATEGORIES.map((tab) => {
        const isActive = activeTab === tab.id;
        const dirtyCount = categoryDirtyCounts[tab.id] || 0;

        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`settings-tab-btn ${isActive ? "active" : ""}`}
            onClick={() => onSelectTab(tab.id)}
          >
            <Icon type={tab.icon} size={16} />
            <span>{tab.label}</span>
            {dirtyCount > 0 && (
              <span className="settings-tab-dirty-badge" title={`${dirtyCount} unsaved change${dirtyCount > 1 ? "s" : ""}`}>
                {dirtyCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default SettingsTabs;
