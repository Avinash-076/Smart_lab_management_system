import Icon from "../../../../components/ui/Icon";
import "./MemoryCard.css";

export default function MemoryCard({ hardware }) {
  const total =
    hardware?.ram_total_gb !== undefined && hardware?.ram_total_gb !== null
      ? `${hardware.ram_total_gb} GB`
      : "—";
  const usable =
    hardware?.ram_usable_gb !== undefined && hardware?.ram_usable_gb !== null
      ? `${hardware.ram_usable_gb} GB`
      : "—";
  const type = hardware?.ram_type || "—";
  const speed = hardware?.ram_speed || "—";
  const slots =
    hardware?.ram_slots_used !== undefined && hardware?.ram_slots_used !== null
      ? `${hardware.ram_slots_used} / ${hardware.ram_slots_total ?? hardware.ram_slots_used}`
      : "—";

  const rows = [
    { label: "Total Installed", value: total },
    { label: "Usable", value: usable },
    { label: "Type", value: type },
    { label: "Speed", value: speed },
    { label: "Slots Used", value: slots },
  ];

  return (
    <div className="hw-mini-card">
      <div className="hw-mini-header">
        <div className="hw-mini-icon-box hw-icon-green">
          <Icon type="ram" size={17} />
        </div>
        <h4 className="hw-mini-title">Memory (RAM)</h4>
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
