import Icon from "../../../../components/ui/Icon";
import "./MotherboardCard.css";

export default function MotherboardCard({ hardware }) {
  const manufacturer = hardware?.motherboard_manufacturer || "—";
  const model = hardware?.motherboard_model || "—";
  const chipset = hardware?.motherboard_chipset || "—";
  const serial = hardware?.motherboard_serial || "—";

  const colLeft = [
    { label: "Manufacturer", value: manufacturer },
    { label: "Model", value: model },
  ];

  const colRight = [
    { label: "Chipset", value: chipset },
    { label: "Serial Number", value: serial },
  ];

  return (
    <div className="hw-card hw-card-motherboard">
      <div className="hw-card-header">
        <div className="hw-card-icon-box hw-icon-blue">
          <Icon type="motherboard" size={18} />
        </div>
        <h3 className="hw-card-title">Motherboard</h3>
      </div>

      <div className="hw-card-content">
        <div className="hw-two-col-grid">
          <div className="hw-sub-col">
            {colLeft.map((row, idx) => (
              <div key={idx} className="hw-kv-row">
                <span className="hw-kv-label">{row.label}</span>
                <span className="hw-kv-colon">:</span>
                <span className="hw-kv-value" title={String(row.value)}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>

          <div className="hw-sub-col">
            {colRight.map((row, idx) => (
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
    </div>
  );
}
