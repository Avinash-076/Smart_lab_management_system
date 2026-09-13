import Icon from "./Icon";

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
            <th>Operating System ↕</th>
            <th>CPU</th>
            <th>RAM</th>
            <th>Disk (Free / Total)</th>
            <th>Last Seen ↕</th>
            <th>Status ↕</th>
            <th>Actions</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((pc) => {
            const used = Math.round(
              ((pc.total - pc.free) / pc.total) * 100
            );

            return (
              <tr key={pc.id}>
                <td>
                  <div className="pc-name">
                    <Icon
                      type="windows"
                      size={20}
                    />

                    <b>{pc.name}</b>
                  </div>
                </td>

                <td>{pc.ip}</td>

                <td>{pc.os}</td>

                <td>
                  {pc.cpu.split(" @ ")[0]}
                  <br />
                  @{" "}
                  {pc.cpu.split(" @ ")[1]}
                </td>

                <td>{pc.ram}</td>

                <td>
                  <div className="disk">
                    <div className="disk-label">
                      <span>
                        {pc.free} GB / {pc.total} GB
                      </span>

                      <span>{used}%</span>
                    </div>

                    <div className="disk-track">
                      <div
                        className="disk-fill"
                        style={{
                          width: `${used}%`,
                        }}
                      />
                    </div>
                  </div>
                </td>

                <td>
                  {pc.last}
                  <br />
                  {pc.time}
                </td>

                <td>
                  <span
                    className={`status ${pc.status.toLowerCase()}`}
                  >
                    <i />
                    {pc.status}
                  </span>
                </td>

                <td>
                  <div className="actions">
                    <button
                      className="view"
                      onClick={() => setView(pc)}
                      title="View"
                    >
                      <Icon
                        type="eye"
                        size={16}
                      />
                    </button>

                    <button
                      className="edit"
                      onClick={() => setEdit(pc)}
                      title="Edit"
                    >
                      <Icon
                        type="edit"
                        size={16}
                      />
                    </button>

                    <button
                      className="delete"
                      onClick={() => del(pc.id)}
                      title="Delete"
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