import Icon from "../../../../components/ui/Icon";
import "./NetworkInfoCard.css";

export default function NetworkInfoCard({ computer, hardware }) {
  const ip = computer?.ip_address || "—";
  const mac = computer?.mac_address || "—";
  const subnet = hardware?.subnet_mask || "—";
  const gateway = hardware?.default_gateway || "—";
  const dns = hardware?.dns_servers || "—";
  const connection = hardware?.connection_type || "—";

  const colLeft = [
    { label: "IP Address", value: ip },
    { label: "Subnet Mask", value: subnet },
    { label: "Gateway", value: gateway },
  ];

  const colRight = [
    { label: "DNS Server", value: dns },
    { label: "MAC Address", value: mac, isMono: true },
    { label: "Connection", value: connection },
  ];

  return (
    <div className="hw-card hw-card-network">
      <div className="hw-card-header">
        <div className="hw-card-icon-box hw-icon-blue">
          <Icon type="network" size={18} />
        </div>
        <h3 className="hw-card-title">Network Information</h3>
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
                <span
                  className={`hw-kv-value ${row.isMono ? "hw-mono" : ""}`}
                  title={String(row.value)}
                >
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
