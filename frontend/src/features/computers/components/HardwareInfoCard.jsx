import Icon from "../../../components/ui/Icon";
import "./HardwareInfoCard.css";

export default function HardwareInfoCard({ computer, hardware }) {
  const hostname = computer?.hostname || `PC-${computer?.id || ""}`;
  const fullOs = `${computer?.os_name || ""} ${computer?.os_version || ""}`.trim() || "—";

  const rows = [
    { label: "Computer Name", value: hostname },
    { label: "Manufacturer", value: hardware?.manufacturer || "—" },
    { label: "Model", value: hardware?.model || "—" },
    { label: "Serial Number", value: hardware?.serial_number || "—" },
    { label: "Operating System", value: fullOs },
    { label: "System Type", value: hardware?.system_type || "—" },
    { label: "BIOS Version", value: hardware?.bios_version || "—" },
    { label: "BIOS Date", value: hardware?.bios_date || "—" },
  ];

  return (
    <div className="hw-card hw-card-main">
      <div className="hw-card-header">
        <div className="hw-card-icon-box hw-icon-blue">
          <Icon type="chip" size={18} />
        </div>
        <h3 className="hw-card-title">Hardware Information</h3>
      </div>

      <div className="hw-card-content">
        <div className="hw-key-value-list">
          {rows.map((row, idx) => (
            <div key={idx} className="hw-kv-row">
              <span className="hw-kv-label">{row.label}</span>
              <span className="hw-kv-colon">:</span>
              <span className="hw-kv-value" title={String(row.value)}>
                {row.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
