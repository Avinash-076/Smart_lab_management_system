import { useMemo, useState } from "react";

import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

/* =====================================================
   SOFTWARE DATA
===================================================== */

const softwareData = [
  {
    id: 1,
    name: "Google Chrome",
    version: "136.0.7103.114",
    category: "Browser",
    computer: "PC-01",
    installed: "10 May 2025",
    status: "Up to Date",
  },
  {
    id: 2,
    name: "Mozilla Firefox",
    version: "138.0",
    category: "Browser",
    computer: "PC-02",
    installed: "08 May 2025",
    status: "Up to Date",
  },
  {
    id: 3,
    name: "Microsoft Edge",
    version: "136.0.3240.76",
    category: "Browser",
    computer: "PC-03",
    installed: "12 May 2025",
    status: "Up to Date",
  },
  {
    id: 4,
    name: "Visual Studio Code",
    version: "1.100.2",
    category: "Development",
    computer: "PC-04",
    installed: "15 May 2025",
    status: "Up to Date",
  },
  {
    id: 5,
    name: "Python",
    version: "3.11.9",
    category: "Development",
    computer: "PC-05",
    installed: "03 May 2025",
    status: "Up to Date",
  },
  {
    id: 6,
    name: "Node.js",
    version: "20.15.1",
    category: "Development",
    computer: "PC-06",
    installed: "05 May 2025",
    status: "Outdated",
  },
  {
    id: 7,
    name: "Git",
    version: "2.49.0",
    category: "Development",
    computer: "PC-07",
    installed: "06 May 2025",
    status: "Up to Date",
  },
  {
    id: 8,
    name: "MySQL Workbench",
    version: "8.0.41",
    category: "Database",
    computer: "PC-08",
    installed: "07 May 2025",
    status: "Up to Date",
  },
  {
    id: 9,
    name: "Postman",
    version: "11.45.0",
    category: "Development",
    computer: "PC-09",
    installed: "11 May 2025",
    status: "Up to Date",
  },
  {
    id: 10,
    name: "VLC Media Player",
    version: "3.0.21",
    category: "Multimedia",
    computer: "PC-10",
    installed: "09 May 2025",
    status: "Up to Date",
  },
  {
    id: 11,
    name: "7-Zip",
    version: "24.09",
    category: "Utilities",
    computer: "PC-11",
    installed: "02 May 2025",
    status: "Up to Date",
  },
  {
    id: 12,
    name: "Adobe Acrobat Reader",
    version: "24.005.20320",
    category: "Office",
    computer: "PC-12",
    installed: "04 May 2025",
    status: "Outdated",
  },
  {
    id: 13,
    name: "Microsoft Word",
    version: "2021",
    category: "Office",
    computer: "PC-13",
    installed: "01 May 2025",
    status: "Up to Date",
  },
  {
    id: 14,
    name: "Microsoft Excel",
    version: "2021",
    category: "Office",
    computer: "PC-14",
    installed: "01 May 2025",
    status: "Up to Date",
  },
  {
    id: 15,
    name: "Microsoft PowerPoint",
    version: "2021",
    category: "Office",
    computer: "PC-15",
    installed: "01 May 2025",
    status: "Up to Date",
  },
  {
    id: 16,
    name: "Java",
    version: "21.0.6",
    category: "Development",
    computer: "PC-16",
    installed: "13 May 2025",
    status: "Up to Date",
  },
  {
    id: 17,
    name: "IntelliJ IDEA",
    version: "2025.1",
    category: "Development",
    computer: "PC-17",
    installed: "14 May 2025",
    status: "Up to Date",
  },
  {
    id: 18,
    name: "PyCharm",
    version: "2025.1",
    category: "Development",
    computer: "PC-18",
    installed: "14 May 2025",
    status: "Up to Date",
  },
  {
    id: 19,
    name: "GitHub Desktop",
    version: "3.4.17",
    category: "Development",
    computer: "PC-19",
    installed: "16 May 2025",
    status: "Up to Date",
  },
  {
    id: 20,
    name: "Notepad++",
    version: "8.7.9",
    category: "Utilities",
    computer: "PC-20",
    installed: "03 May 2025",
    status: "Outdated",
  },
  {
    id: 21,
    name: "WinRAR",
    version: "7.01",
    category: "Utilities",
    computer: "PC-21",
    installed: "05 May 2025",
    status: "Up to Date",
  },
  {
    id: 22,
    name: "Cisco Packet Tracer",
    version: "8.2.2",
    category: "Networking",
    computer: "PC-22",
    installed: "10 May 2025",
    status: "Up to Date",
  },
  {
    id: 23,
    name: "Wireshark",
    version: "4.4.5",
    category: "Networking",
    computer: "PC-23",
    installed: "12 May 2025",
    status: "Up to Date",
  },
  {
    id: 24,
    name: "Android Studio",
    version: "2024.3.2",
    category: "Development",
    computer: "PC-24",
    installed: "15 May 2025",
    status: "Outdated",
  },
];

/* =====================================================
   COMPONENT
===================================================== */

function SoftwareInventory() {
  const [search, setSearch] =
    useState("");

  const [category, setCategory] =
    useState("All Categories");

  const [computer, setComputer] =
    useState("All Computers");

  const [status, setStatus] =
    useState("All Status");

  /* =====================================================
     CATEGORIES
  ===================================================== */

  const categories = [
    ...new Set(
      softwareData.map(
        (software) =>
          software.category
      )
    ),
  ];

  /* =====================================================
     COMPUTERS
  ===================================================== */

  const computers = [
    ...new Set(
      softwareData.map(
        (software) =>
          software.computer
      )
    ),
  ];

  /* =====================================================
     FILTER DATA
  ===================================================== */

  const filteredSoftware =
    useMemo(() => {
      const searchText =
        search
          .toLowerCase()
          .trim();

      return softwareData.filter(
        (software) => {
          const matchesSearch =
            !searchText ||
            software.name
              .toLowerCase()
              .includes(
                searchText
              ) ||
            software.version
              .toLowerCase()
              .includes(
                searchText
              ) ||
            software.computer
              .toLowerCase()
              .includes(
                searchText
              );

          const matchesCategory =
            category ===
              "All Categories" ||
            software.category ===
              category;

          const matchesComputer =
            computer ===
              "All Computers" ||
            software.computer ===
              computer;

          const matchesStatus =
            status ===
              "All Status" ||
            software.status ===
              status;

          return (
            matchesSearch &&
            matchesCategory &&
            matchesComputer &&
            matchesStatus
          );
        }
      );
    }, [
      search,
      category,
      computer,
      status,
    ]);

  /* =====================================================
     STATISTICS
  ===================================================== */

  const totalSoftware =
    softwareData.length;

  const totalComputers =
    new Set(
      softwareData.map(
        (software) =>
          software.computer
      )
    ).size;

  const outdatedSoftware =
    softwareData.filter(
      (software) =>
        software.status ===
        "Outdated"
    ).length;

  const totalCategories =
    categories.length;

  /* =====================================================
     RESET FILTERS
  ===================================================== */

  const resetFilters = () => {
    setSearch("");
    setCategory(
      "All Categories"
    );
    setComputer(
      "All Computers"
    );
    setStatus("All Status");
  };

  /* =====================================================
     RETURN
  ===================================================== */

  return (
    <div className="content">

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-top">

        <div>
          <h2>
            Software Inventory
          </h2>

          <p>
            View software installed
            on laboratory computers.
          </p>
        </div>

      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}

      <div className="cards">

        <StatCard
          icon="software"
          title="Total Software"
          number={
            totalSoftware
          }
          footer="Installed applications"
          type="blue"
        />

        <StatCard
          icon="computer"
          title="Computers"
          number={
            totalComputers
          }
          footer="Computers reporting software"
          type="green"
        />

        <StatCard
          icon="issue"
          title="Outdated"
          number={
            outdatedSoftware
          }
          footer="Software requiring updates"
          type="orange"
        />

        <StatCard
          icon="details"
          title="Categories"
          number={
            totalCategories
          }
          footer="Software categories"
          type="purple"
        />

      </div>

      {/* =================================================
          SOFTWARE TABLE
      ================================================= */}

      <div className="table-card">

        {/* TABLE HEADER */}

        <div className="page-section-header">

          <div>
            <h3>
              Installed Software
            </h3>

            <p>
              Software inventory
              collected from client
              agents.
            </p>
          </div>

        </div>

        {/* =================================================
            FILTERS
        ================================================= */}

        <div className="filters">

          {/* SEARCH */}

          <div className="table-search">

            <input
              value={search}
              onChange={(e) =>
                setSearch(
                  e.target.value
                )
              }
              placeholder="Search software, version, computer..."
            />

            <Icon
              type="search"
              size={18}
            />

          </div>

          {/* CATEGORY */}

          <select
            value={category}
            onChange={(e) =>
              setCategory(
                e.target.value
              )
            }
          >
            <option>
              All Categories
            </option>

            {categories.map(
              (item) => (
                <option
                  key={item}
                  value={item}
                >
                  {item}
                </option>
              )
            )}

          </select>

          {/* COMPUTER */}

          <select
            value={computer}
            onChange={(e) =>
              setComputer(
                e.target.value
              )
            }
          >
            <option>
              All Computers
            </option>

            {computers.map(
              (item) => (
                <option
                  key={item}
                  value={item}
                >
                  {item}
                </option>
              )
            )}

          </select>

          {/* STATUS */}

          <select
            value={status}
            onChange={(e) =>
              setStatus(
                e.target.value
              )
            }
          >
            <option>
              All Status
            </option>

            <option>
              Up to Date
            </option>

            <option>
              Outdated
            </option>

          </select>

          {/* RESET */}

          <button
            className="refresh"
            onClick={
              resetFilters
            }
          >
            <Icon
              type="refresh"
              size={17}
            />

            Reset
          </button>

        </div>

        {/* =================================================
            RESULT COUNT
        ================================================= */}

        <div
          style={{
            padding:
              "0 20px 15px",
            fontSize: "12px",
            color: "#718099",
          }}
        >
          Showing{" "}
          <strong>
            {
              filteredSoftware.length
            }
          </strong>{" "}
          software records
        </div>

        {/* =================================================
            TABLE
        ================================================= */}

        {filteredSoftware.length >
        0 ? (
          <div className="table-scroll">

            <table>

              <thead>

                <tr>

                  <th>
                    Software Name
                  </th>

                  <th>
                    Version
                  </th>

                  <th>
                    Category
                  </th>

                  <th>
                    Computer
                  </th>

                  <th>
                    Installed
                  </th>

                  <th>
                    Status
                  </th>

                </tr>

              </thead>

              <tbody>

                {filteredSoftware.map(
                  (software) => (
                    <tr
                      key={
                        software.id
                      }
                    >

                      {/* SOFTWARE */}

                      <td>

                        <div
                          style={{
                            display:
                              "flex",
                            alignItems:
                              "center",
                            gap: "10px",
                          }}
                        >

                          <div
                            style={{
                              width:
                                "34px",
                              height:
                                "34px",
                              borderRadius:
                                "8px",
                              background:
                                "#eef4ff",
                              display:
                                "flex",
                              alignItems:
                                "center",
                              justifyContent:
                                "center",
                              color:
                                "#2563eb",
                            }}
                          >

                            <Icon
                              type="software"
                              size={18}
                            />

                          </div>

                          <strong>
                            {
                              software.name
                            }
                          </strong>

                        </div>

                      </td>

                      {/* VERSION */}

                      <td>
                        {
                          software.version
                        }
                      </td>

                      {/* CATEGORY */}

                      <td>

                        <span
                          style={{
                            display:
                              "inline-block",
                            padding:
                              "5px 9px",
                            borderRadius:
                              "6px",
                            background:
                              "#f3f5f8",
                            fontSize:
                              "11px",
                            color:
                              "#536078",
                            fontWeight:
                              "600",
                          }}
                        >
                          {
                            software.category
                          }
                        </span>

                      </td>

                      {/* COMPUTER */}

                      <td>

                        <strong>
                          {
                            software.computer
                          }
                        </strong>

                      </td>

                      {/* INSTALLED */}

                      <td>
                        {
                          software.installed
                        }
                      </td>

                      {/* STATUS */}

                      <td>

                        <span
                          className={
                            `status ${
                              software.status ===
                              "Outdated"
                                ? "offline"
                                : "online"
                            }`
                          }
                        >

                          <i />

                          {
                            software.status
                          }

                        </span>

                      </td>

                    </tr>
                  )
                )}

              </tbody>

            </table>

          </div>
        ) : (

          /* =================================================
             EMPTY SEARCH RESULT
          ================================================= */

          <div className="empty-state">

            <Icon
              type="software"
              size={40}
            />

            <h3>
              No software found
            </h3>

            <p>
              No software matches
              the selected filters.
            </p>

            <button
              className="modal-button"
              onClick={
                resetFilters
              }
            >
              Clear Filters
            </button>

          </div>

        )}

      </div>

    </div>
  );
}

export default SoftwareInventory;