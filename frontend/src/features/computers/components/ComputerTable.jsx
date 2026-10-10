import Icon from "../../../components/ui/Icon";

function formatLastSeen(dateStr) {
  if (!dateStr) return "Never";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return "Never";
  }
}

function ComputerTable({
  rows,
  setView,
  setEdit,
  del,
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Computer Name ↕</th>
            <th>IP Address ↕</th>
            <th>MAC Address</th>
            <th>Operating System ↕</th>
            <th>Last Seen ↕</th>
            <th>Status ↕</th>
            <th>Actions</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((pc) => {
            const hostname = pc.hostname || pc.name || `PC-${pc.id}`;
            const ip = pc.ip_address || pc.ip || "—";
            const mac = pc.mac_address || "—";
            const os = pc.os_name
              ? `${pc.os_name} ${pc.os_version || ""}`.trim()
              : pc.os || "—";
            const status = (pc.status || "offline").toLowerCase();
            const statusLabel =
              status.charAt(0).toUpperCase() + status.slice(1);
            const isWindows =
              os.toLowerCase().includes("windows");

            return (
              <tr key={pc.id}>
                <td>
                  <div className="pc-name">
                    <Icon
                      type={isWindows ? "windows" : "computer"}
                      size={20}
                    />
                    <b>{hostname}</b>
                  </div>
                </td>

                <td>{ip}</td>

                <td>
                  <code style={{ fontSize: "12px", color: "#4b5563" }}>
                    {mac}
                  </code>
                </td>

                <td>{os}</td>

                <td>{formatLastSeen(pc.last_seen)}</td>

                <td>
                  <span className={`status ${status}`}>
                    <i />
                    {statusLabel}
                  </span>
                </td>

                <td>
                  <div className="actions">
                    <button
                      className="view"
                      onClick={() => setView(pc)}
                      title="View Computer Details"
                    >
                      <Icon
                        type="eye"
                        size={16}
                      />
                    </button>

                    <button
                      className="edit"
                      onClick={() => setEdit(pc)}
                      title="Edit Computer"
                    >
                      <Icon
                        type="edit"
                        size={16}
                      />
                    </button>

                    <button
                      className="delete"
                      onClick={() => del(pc.id)}
                      title="Delete Computer"
                    >
                      <Icon
                        type="trash"
                        size={16}
                      />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default ComputerTable;