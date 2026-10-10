import { useState, useEffect, useCallback, useMemo } from "react";
import { getComputers, getComputerSoftware } from "../../../services/api";
import StatCard from "../../../components/ui/StatCard";
import Icon from "../../../components/ui/Icon";

function SoftwareInventory() {
  const [computers, setComputers] = useState([]);
  const [selectedComputerId, setSelectedComputerId] = useState("");
  const [softwareList, setSoftwareList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [publisherFilter, setPublisherFilter] = useState("All Publishers");

  // Load computers list on mount
  useEffect(() => {
    let ignore = false;
    async function loadComputers() {
      try {
        const list = await getComputers();
        if (ignore) return;
        if (Array.isArray(list)) {
          setComputers(list);
          if (list.length > 0) {
            setSelectedComputerId(String(list[0].id));
          }
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load computers list.");
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    loadComputers();
    return () => {
      ignore = true;
    };
  }, []);

  // Load software for selected computer
  const loadSoftware = useCallback(async () => {
    if (!selectedComputerId) {
      setSoftwareList([]);
      return;
    }

    try {
      setLoading(true);
      setError("");
      const data = await getComputerSoftware(Number(selectedComputerId));
      if (Array.isArray(data)) {
        setSoftwareList(data);
      } else {
        setSoftwareList([]);
      }
    } catch (err) {
      console.warn("Could not fetch software inventory:", err);
      setError(err.message || "Failed to load software inventory.");
      setSoftwareList([]);
    } finally {
      setLoading(false);
    }
  }, [selectedComputerId]);

  useEffect(() => {
    if (!selectedComputerId) {
      return;
    }
    let ignore = false;
    async function fetchSoftware() {
      try {
        setError("");
        const data = await getComputerSoftware(Number(selectedComputerId));
        if (ignore) return;
        if (Array.isArray(data)) {
          setSoftwareList(data);
        } else {
          setSoftwareList([]);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load software inventory.");
          setSoftwareList([]);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    fetchSoftware();
    return () => {
      ignore = true;
    };
  }, [selectedComputerId]);

  // Unique publishers for filtering
  const publishers = useMemo(() => {
    const set = new Set();
    softwareList.forEach((item) => {
      if (item.publisher && item.publisher.trim()) {
        set.add(item.publisher.trim());
      }
    });
    return ["All Publishers", ...Array.from(set).sort()];
  }, [softwareList]);

  // Filtered software
  const filteredSoftware = useMemo(() => {
    const q = search.toLowerCase().trim();
    return softwareList.filter((item) => {
      const matchesSearch =
        !q ||
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.version && item.version.toLowerCase().includes(q)) ||
        (item.publisher && item.publisher.toLowerCase().includes(q));

      const matchesPublisher =
        publisherFilter === "All Publishers" ||
        item.publisher === publisherFilter;

      return matchesSearch && matchesPublisher;
    });
  }, [softwareList, search, publisherFilter]);

  const resetFilters = () => {
    setSearch("");
    setPublisherFilter("All Publishers");
  };

  const selectedComputerObj = computers.find(
    (c) => String(c.id) === String(selectedComputerId)
  );

  return (
    <div className="content">
      {/* =================================================
          PAGE HEADER
      ================================================= */}
      <div className="page-top">
        <div>
          <h2>Software Inventory</h2>
          <p>View applications installed on laboratory computers.</p>
        </div>

        <div className="top-actions">
          <button
            className="refresh"
            onClick={loadSoftware}
            disabled={loading}
            title="Refresh software list"
          >
            <Icon type="refresh" size={16} />
            Refresh
          </button>
        </div>
      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}
      <div className="cards">
        <StatCard
          icon="software"
          title="Installed Applications"
          number={softwareList.length}
          footer={
            selectedComputerObj
              ? `Installed on ${selectedComputerObj.hostname}`
              : "Selected computer applications"
          }
          type="blue"
        />

        <StatCard
          icon="computer"
          title="Total Computers"
          number={computers.length}
          footer="Registered lab computers"
          type="green"
        />

        <StatCard
          icon="details"
          title="Publishers / Vendors"
          number={publishers.length > 1 ? publishers.length - 1 : 0}
          footer="Software vendors"
          type="purple"
        />

        <StatCard
          icon="computer"
          title="Selected Target"
          number={selectedComputerObj?.hostname || "—"}
          footer={selectedComputerObj?.ip_address || "No target selected"}
          type="orange"
        />
      </div>

      {/* =================================================
          SOFTWARE TABLE CARD
      ================================================= */}
      <div className="table-card">
        <div className="page-section-header">
          <div>
            <h3>Installed Applications</h3>
            <p>Registry-discovered software inventory from client agent.</p>
          </div>
        </div>

        {/* FILTERS */}
        <div className="filters">
          <div className="table-search">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search software, version, publisher..."
            />
            <Icon type="search" size={18} />
          </div>

          {/* COMPUTER SELECTOR */}
          <select
            value={selectedComputerId}
            onChange={(e) => {
              setSelectedComputerId(e.target.value);
              resetFilters();
            }}
          >
            {computers.length === 0 && <option value="">No Computers Available</option>}
            {computers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.hostname} (#{c.id})
              </option>
            ))}
          </select>

          {/* PUBLISHER SELECTOR */}
          <select
            value={publisherFilter}
            onChange={(e) => setPublisherFilter(e.target.value)}
          >
            {publishers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          <button className="export" onClick={resetFilters}>
            <Icon type="refresh" size={16} />
            Reset
          </button>
        </div>

        {/* RESULT COUNT */}
        <div
          style={{
            padding: "0 20px 15px",
            fontSize: "12px",
            color: "#718099",
          }}
        >
          Showing <strong>{filteredSoftware.length}</strong> of{" "}
          <strong>{softwareList.length}</strong> software records
        </div>

        {/* TABLE OR STATES */}
        {loading && softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="refresh" size={36} />
            <h3>Loading software inventory...</h3>
            <p>Fetching installed software registry from server.</p>
          </div>
        ) : error && softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <h3 style={{ color: "#dc2626" }}>Failed to load software</h3>
            <p>{error}</p>
            <button
              className="refresh"
              onClick={loadSoftware}
              style={{ marginTop: "12px", display: "inline-flex" }}
            >
              Try Again
            </button>
          </div>
        ) : softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="software" size={40} />
            <h3>No software inventory recorded</h3>
            <p>
              The client agent has not reported installed applications for this
              computer yet.
            </p>
          </div>
        ) : filteredSoftware.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="software" size={36} />
            <h3>No software found</h3>
            <p>No applications match the current search or filters.</p>
            <button
              className="export"
              onClick={resetFilters}
              style={{ marginTop: "12px", display: "inline-flex" }}
            >
              Clear Filters
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "35%" }}>Software Name</th>
                  <th style={{ width: "20%" }}>Version</th>
                  <th style={{ width: "25%" }}>Publisher / Vendor</th>
                  <th style={{ width: "20%" }}>Install Date</th>
                </tr>
              </thead>
              <tbody>
                {filteredSoftware.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <div
                          style={{
                            width: "32px",
                            height: "32px",
                            borderRadius: "6px",
                            background: "#eff6ff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#2563eb",
                            flexShrink: 0,
                          }}
                        >
                          <Icon type="software" size={16} />
                        </div>
                        <strong style={{ color: "#1e293b", fontSize: "12px" }}>
                          {item.name}
                        </strong>
                      </div>
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: "12px",
                          color: "#475569",
                          background: "#f1f5f9",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {item.version || "—"}
                      </code>
                    </td>
                    <td style={{ color: "#475569", fontSize: "12px" }}>
                      {item.publisher || "—"}
                    </td>
                    <td style={{ color: "#64748b", fontSize: "12px" }}>
                      {item.install_date || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default SoftwareInventory;