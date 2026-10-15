import Icon from "../../../../components/ui/Icon";
import "./GraphicsCard.css";

export default function GraphicsCard({ hardware }) {
  const adapter = hardware?.gpu_name || "—";
  const dedicated =
    hardware?.gpu_memory_mb !== undefined && hardware?.gpu_memory_mb !== null
      ? `${hardware.gpu_memory_mb} MB`
      : "—";
  const driver = hardware?.gpu_driver_version || "—";

  const rows = [
    { label: "Adapter", value: adapter },
    { label: "Dedicated", value: dedicated },
    { label: "Driver Version", value: driver },
  ];

  return (
    <div className="hw-mini-card">
      <div className="hw-mini-header">
        <div className="hw-mini-icon-box hw-icon-purple">
          <Icon type="gpu" size={17} />
        </div>
        <h4 className="hw-mini-title">Graphics</h4>
      </div>

      <div className="hw-mini-list">
        {rows.map((row, idx) => (
          <div key={idx} className="hw-mini-row">
            <span className="hw-mini-label">{row.label}</span>
            <span className="hw-mini-colon">:</span>
            <span className="hw-mini-value" title={String(row.value)}>
              {row.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
