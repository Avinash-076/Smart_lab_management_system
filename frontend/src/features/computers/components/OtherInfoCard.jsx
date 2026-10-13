import Icon from "../../../components/ui/Icon";
import { parseUptimeString } from "../utils/computerUtils";
import "./OtherInfoCard.css";

export default function OtherInfoCard({ hardware, uptimeText }) {
  const uptime = parseUptimeString(hardware?.last_boot_time) || uptimeText || "—";
  const installDate = hardware?.os_install_date || "—";
  const bootTime = hardware?.last_boot_time || "—";
  const powerPlan = hardware?.power_plan || "—";

  const rows = [
    { label: "System Uptime", value: uptime },
    { label: "Windows Install Date", value: installDate },
    { label: "Last Boot Time", value: bootTime },
    { label: "Power Plan", value: powerPlan },
  ];

  return (
    <div className="hw-mini-card">
      <div className="hw-mini-header">
        <div className="hw-mini-icon-box hw-icon-blue">
          <Icon type="info" size={17} />
        </div>
        <h4 className="hw-mini-title">Other Information</h4>
      </div>

      <div className="hw-mini-list">
        {rows.map((row, idx) => (
          <div key={idx} className="hw-mini-row">
            <span className="hw-mini-label hw-label-wide">{row.label}</span>
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
