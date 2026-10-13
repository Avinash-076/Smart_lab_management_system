import Icon from "../../../components/ui/Icon";
import "./ProcessorCard.css";

export default function ProcessorCard({ hardware }) {
  const rows = [
    { label: "Name", value: hardware?.processor_name || "—" },
    { label: "Cores", value: hardware?.processor_cores ?? "—" },
    { label: "Threads", value: hardware?.processor_threads ?? "—" },
    { label: "Base Speed", value: hardware?.processor_base_speed || "—" },
    { label: "Max Speed", value: hardware?.processor_max_speed || "—" },
  ];

  return (
    <div className="hw-mini-card">
      <div className="hw-mini-header">
        <div className="hw-mini-icon-box hw-icon-blue">
          <Icon type="chip" size={17} />
        </div>
        <h4 className="hw-mini-title">Processor</h4>
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
