import { describe, it, expect, vi } from "vitest";
import { renderToString } from "react-dom/server";
import ComputerSummaryCards from "../features/computers/components/ComputerSummaryCards";
import ComputerFilters from "../features/computers/components/ComputerFilters";
import ComputerTable from "../features/computers/components/ComputerTable";
import ComputerPagination from "../features/computers/components/ComputerPagination";
import DeleteConfirmModal from "../features/computers/components/DeleteConfirmModal";
import {
  calculateComputerStats,
  isWindowsOS,
  getDiskMetrics,
  formatLastSeen,
  getOsIconInfo,
  getPaginationItems,
} from "../features/computers/utils/computerUtils";

describe("Computers Feature - Unit & Layout Tests", () => {
  const sampleComputers = [
    {
      id: 1,
      hostname: "PC-01",
      ip_address: "192.168.1.101",
      mac_address: "00:1A:2B:3C:4D:5E",
      os_name: "Windows 11 Pro 64-bit",
      status: "online",
      cpu: "Intel Core i5-10400 @ 2.90GHz",
      ram: "16 GB",
      disk_free: 256,
      disk_total: 512,
      last_seen: "2025-05-21T10:15:00Z",
    },
    {
      id: 2,
      hostname: "PC-02",
      ip_address: "192.168.1.102",
      mac_address: "00:1A:2B:3C:4D:5F",
      os_name: "Windows 10 Pro 64-bit",
      status: "online",
      cpu: "Intel Core i5-9400 @ 2.90GHz",
      ram: 8,
      disk_free: 120,
      disk_total: 256,
      last_seen: "2025-05-21T10:14:00Z",
    },
    {
      id: 3,
      hostname: "PC-03",
      ip_address: "192.168.1.103",
      mac_address: "00:1A:2B:3C:4D:60",
      os_name: "Windows 11 Pro 64-bit",
      status: "online",
      cpu: "Intel Core i7-10700 @ 2.90GHz",
      ram: "16 GB",
      disk_free: 300,
      disk_total: 512,
      last_seen: "2025-05-21T10:12:00Z",
    },
    {
      id: 4,
      hostname: "PC-04",
      ip_address: "192.168.1.104",
      mac_address: "00:1A:2B:3C:4D:61",
      os_name: "Ubuntu 22.04 LTS 64-bit",
      status: "online",
      cpu: "Intel Core i5-10400 @ 2.90GHz",
      ram: "8 GB",
      disk_free: 180,
      disk_total: 256,
      last_seen: "2025-05-21T10:11:00Z",
    },
    {
      id: 5,
      hostname: "PC-05",
      ip_address: "192.168.1.105",
      mac_address: "00:1A:2B:3C:4D:62",
      os_name: "Windows 10 Pro 64-bit",
      status: "offline",
      cpu: "Intel Core i3-9100 @ 3.60GHz",
      ram: "8 GB",
      disk_free: 80,
      disk_total: 256,
      last_seen: "2025-05-21T10:11:00Z",
    },
    {
      id: 6,
      hostname: "PC-06",
      ip_address: "192.168.1.106",
      mac_address: "00:1A:2B:3C:4D:63",
      os_name: "Windows 11 Pro 64-bit",
      status: "online",
      cpu: "Intel Core i5-11400 @ 2.60GHz",
      ram: "16 GB",
      disk_free: 200,
      disk_total: 512,
      last_seen: "2025-05-21T09:58:00Z",
    },
    {
      id: 7,
      hostname: "PC-07",
      ip_address: "192.168.1.107",
      mac_address: "00:1A:2B:3C:4D:64",
      os_name: "macOS Sonoma 14.5",
      status: "offline",
      cpu: "Apple M1 @ 3.20GHz",
      ram: "8 GB",
      disk_free: 40,
      disk_total: 128,
      last_seen: "2025-05-21T09:45:00Z",
    },
    {
      id: 8,
      hostname: "PC-08",
      ip_address: "192.168.1.108",
      mac_address: "00:1A:2B:3C:4D:65",
      os_name: "Debian 12 64-bit",
      status: "online",
      cpu: "Intel Core i5-9400 @ 2.90GHz",
      ram: "8 GB",
      disk_free: 150,
      disk_total: 256,
      last_seen: "2025-05-21T09:40:00Z",
    },
  ];

  /* --------------------------------------------------
     1. Summary Card Calculations & Mutual Exclusivity
  -------------------------------------------------- */
  describe("Summary Card Calculations", () => {
    it("correctly calculates counts and percentages from real data", () => {
      const stats = calculateComputerStats(sampleComputers);

      expect(stats.total).toBe(8);
      expect(stats.online).toBe(6);
      expect(stats.onlinePct).toBe("75.00% of total");
      expect(stats.offline).toBe(2);
      expect(stats.offlinePct).toBe("25.00% of total");
      expect(stats.windows).toBe(5);
      expect(stats.windowsPct).toBe("62.50% of total");
      expect(stats.otherOS).toBe(3);
      expect(stats.otherOSPct).toBe("37.50% of total");

      // Mutual exclusivity & exhaustive count
      expect(stats.windows + stats.otherOS).toBe(stats.total);
      expect(stats.online + stats.offline).toBe(stats.total);
    });

    it("safely handles empty datasets without division-by-zero errors", () => {
      const stats = calculateComputerStats([]);

      expect(stats.total).toBe(0);
      expect(stats.online).toBe(0);
      expect(stats.onlinePct).toBe("0.00% of total");
      expect(stats.offline).toBe(0);
      expect(stats.offlinePct).toBe("0.00% of total");
      expect(stats.windows).toBe(0);
      expect(stats.windowsPct).toBe("0.00% of total");
      expect(stats.otherOS).toBe(0);
      expect(stats.otherOSPct).toBe("0.00% of total");
    });

    it("renders ComputerSummaryCards with all 5 cards", () => {
      const html = renderToString(
        <ComputerSummaryCards computers={sampleComputers} />
      );

      expect(html).toContain("Total Computers");
      expect(html).toContain("Online");
      expect(html).toContain("Offline");
      expect(html).toContain("Windows");
      expect(html).toContain("Other OS");
      expect(html).toContain("All computers in lab");
    });
  });

  /* --------------------------------------------------
     2. OS Categorization & Icon Detection
  -------------------------------------------------- */
  describe("OS Categorization & Icons", () => {
    it("distinguishes Windows vs Other OS correctly", () => {
      expect(isWindowsOS({ os_name: "Windows 11 Pro" })).toBe(true);
      expect(isWindowsOS({ os_name: "Microsoft Windows Server 2022" })).toBe(true);
      expect(isWindowsOS({ os_name: "Ubuntu 22.04 LTS" })).toBe(false);
      expect(isWindowsOS({ os_name: "macOS Sonoma" })).toBe(false);
      expect(isWindowsOS(null)).toBe(false);
    });

    it("resolves correct icon types for different operating systems", () => {
      expect(getOsIconInfo({ os_name: "Windows 11" }).type).toBe("windows");
      expect(getOsIconInfo({ os_name: "Ubuntu Linux" }).type).toBe("linux");
      expect(getOsIconInfo({ os_name: "macOS Sonoma 14.5" }).type).toBe("apple");
      expect(getOsIconInfo({ os_name: "FreeBSD" }).type).toBe("computer");
    });
  });

  /* --------------------------------------------------
     3. Disk Calculations & Missing Values
  -------------------------------------------------- */
  describe("Disk Capacity Calculations", () => {
    it("calculates used percentage accurately from free and total", () => {
      const disk = getDiskMetrics({ disk_free: 256, disk_total: 512 });
      expect(disk).not.toBeNull();
      expect(disk.freeGB).toBe(256);
      expect(disk.totalGB).toBe(512);
      expect(disk.usedPct).toBe(50); // ((512 - 256) / 512) * 100 = 50%
    });

    it("returns null for missing, zero, or invalid disk capacities", () => {
      expect(getDiskMetrics({})).toBeNull();
      expect(getDiskMetrics({ disk_free: 10, disk_total: 0 })).toBeNull();
      expect(getDiskMetrics({ disk_free: null, disk_total: null })).toBeNull();
    });
  });

  /* --------------------------------------------------
     4. Date & Timestamp Formatting
  -------------------------------------------------- */
  describe("Last Seen Formatting", () => {
    it("formats ISO timestamps into date and time strings", () => {
      const res = formatLastSeen("2025-05-21T10:15:00Z");
      expect(res.date).toContain("2025");
      expect(res.date).toContain("May");
      expect(res.time).not.toBe("");
    });

    it("returns Never for null or undefined timestamps", () => {
      expect(formatLastSeen(null)).toEqual({ date: "Never", time: "" });
      expect(formatLastSeen("")).toEqual({ date: "Never", time: "" });
    });
  });

  /* --------------------------------------------------
     5. Pagination Logic & Ellipsis
  -------------------------------------------------- */
  describe("Pagination Calculations", () => {
    it("returns direct array when total pages is <= 7", () => {
      expect(getPaginationItems(1, 5)).toEqual([1, 2, 3, 4, 5]);
    });

    it("places ellipsis appropriately for large page counts", () => {
      const items = getPaginationItems(1, 10);
      expect(items).toContain("...");
      expect(items[0]).toBe(1);
      expect(items[items.length - 1]).toBe(10);
    });

    it("renders ComputerPagination with correct summary text and buttons", () => {
      const html = renderToString(
        <ComputerPagination
          page={1}
          pages={5}
          setPage={vi.fn()}
          totalRows={42}
          per={8}
          setPer={vi.fn()}
        />
      );

      expect(html).toContain("Showing 1 to 8 of 42 computers");
      expect(html).toContain("8 / page");
      expect(html).toContain("«");
      expect(html).toContain("»");
    });
  });

  /* --------------------------------------------------
     6. ComputerFilters Component
  -------------------------------------------------- */
  describe("ComputerFilters Component", () => {
    it("renders search input with required placeholder, dropdowns, and Active Filters None", () => {
      const html = renderToString(
        <ComputerFilters
          search=""
          setSearch={vi.fn()}
          os="All OS"
          setOs={vi.fn()}
          status="All Status"
          setStatus={vi.fn()}
          lab="All Labs"
          setLab={vi.fn()}
          sortBy="Name (A-Z)"
          setSortBy={vi.fn()}
          reset={vi.fn()}
        />
      );

      expect(html).toContain("Search by computer name, IP address, or MAC address...");
      expect(html).toContain("All OS");
      expect(html).toContain("All Status");
      expect(html).not.toContain("All Labs");
      expect(html).toContain("Sort by");
      expect(html).toContain("Name (A-Z)");
      expect(html).toContain("Active Filters:");
      expect(html).toContain("None");
      expect(html).toContain("Clear Filters");
    });

    it("displays filter chips when active filters are set", () => {
      const html = renderToString(
        <ComputerFilters
          search="PC-01"
          setSearch={vi.fn()}
          os="Windows"
          setOs={vi.fn()}
          status="Online"
          setStatus={vi.fn()}
          sortBy="Name (A-Z)"
          setSortBy={vi.fn()}
          reset={vi.fn()}
        />
      );

      expect(html).toMatch(/Search: (&quot;|")PC-01(&quot;|")/);
      expect(html).toContain("OS: Windows");
      expect(html).toContain("Status: Online");
      expect(html).not.toContain("None");
    });
  });

  /* --------------------------------------------------
     7. ComputerTable Rendering
  -------------------------------------------------- */
  describe("ComputerTable Component", () => {
    it("renders all 10 table headers, checkboxes, and row data", () => {
      const html = renderToString(
        <ComputerTable
          rows={sampleComputers.slice(0, 2)}
          selectedIds={new Set([1])}
          onToggleSelect={vi.fn()}
          onToggleSelectAll={vi.fn()}
          allPageSelected={false}
          isIndeterminate={true}
          onSort={vi.fn()}
          sortBy="Name (A-Z)"
          setView={vi.fn()}
          setEdit={vi.fn()}
          del={vi.fn()}
        />
      );

      // Check header columns
      expect(html).toContain("Computer Name");
      expect(html).toContain("IP Address");
      expect(html).toContain("Operating System");
      expect(html).toContain("CPU");
      expect(html).toContain("RAM");
      expect(html).toContain("Disk (Free / Total)");
      expect(html).toContain("Last Seen");
      expect(html).toContain("Status");
      expect(html).toContain("Actions");

      // Check row contents
      expect(html).toContain("PC-01");
      expect(html).toContain("192.168.1.101");
      expect(html).toContain("PC-02");
      expect(html).toContain("Online");
      expect(html).toContain("256 GB / 512 GB");
    });
  });

  /* --------------------------------------------------
     8. Delete Confirmation Modal
  -------------------------------------------------- */
  describe("DeleteConfirmModal Component", () => {
    it("renders target computer hostname and confirmation buttons", () => {
      const html = renderToString(
        <DeleteConfirmModal
          computer={{ id: 5, hostname: "PC-05" }}
          onClose={vi.fn()}
          onConfirm={vi.fn()}
        />
      );

      expect(html).toContain("Delete Computer");
      expect(html).toContain("PC-05");
      expect(html).toContain("Cancel");
    });
  });
});
