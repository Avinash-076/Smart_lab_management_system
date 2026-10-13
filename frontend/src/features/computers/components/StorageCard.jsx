import Icon from "../../../components/ui/Icon";
import "./StorageCard.css";

export default function StorageCard({ hardware }) {
  const drives = hardware?.storage_drives_count ?? "—";
  const capacity = hardware?.storage_total_gb ? `${hardware.storage_total_gb} GB` : "—";
  const type = hardware?.storage_type || "—";
  const health = hardware?.storage_health || "—";
  const isHealthGood = typeof health === "string" && (health.toLowerCase().includes("good") || health.toLowerCase().includes("ok"));

  const rows = [
    { label: "Total Drives", value: drives },
    { label: "Total Capacity", value: capacity },
    { label: "Type", value: type },
    {
      label: "Health",
      value: health,
      isHealth: true,
      good: isHealthGood,
    },
  ];

  return (
    <div className="hw-mini-card">
      <div className="hw-mini-header">
        <div className="hw-mini-icon-box hw-icon-orange">
          <Icon type="storage" size={17} />
        </div>
        <h4 className="hw-mini-title">Storage</h4>
      </div>

      <div className="hw-mini-list">
        {rows.map((row, idx) => (
          <div key={idx} className="hw-mini-row">
            <span className="hw-mini-label">{row.label}</span>
            <span className="hw-mini-colon">:</span>
            {row.isHealth ? (
              <span className={`hw-mini-value ${row.good ? "hw-health-good" : ""}`}>
                {row.value}
              </span>
            ) : (
              <span className="hw-mini-value" title={String(row.value)}>
                {row.value}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
