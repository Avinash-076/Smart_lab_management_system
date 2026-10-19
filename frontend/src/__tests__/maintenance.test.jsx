import { describe, it, expect } from "vitest";
import { renderToString } from "react-dom/server";
import MaintenanceHeader from "../features/maintenance/components/MaintenanceHeader/MaintenanceHeader";
import MaintenanceSummaryCards from "../features/maintenance/components/MaintenanceSummaryCards/MaintenanceSummaryCards";
import MaintenanceFilters from "../features/maintenance/components/MaintenanceFilters/MaintenanceFilters";
import MaintenanceTable from "../features/maintenance/components/MaintenanceTable/MaintenanceTable";
import ScheduleMaintenanceModal from "../features/maintenance/components/ScheduleMaintenanceModal/ScheduleMaintenanceModal";
import CompleteMaintenanceModal from "../features/maintenance/components/CompleteMaintenanceModal/CompleteMaintenanceModal";
import MaintenanceDetailsModal from "../features/maintenance/components/MaintenanceDetailsModal/MaintenanceDetailsModal";
import {
  formatDateTime,
  formatDateOnly,
  formatDate,
  getTypeBadgeConfig,
  getStatusBadgeConfig,
  formatStatusText,
  formatTypeText,
  getPaginationItems,
} from "../features/maintenance/utils/maintenanceUtils";

describe("Maintenance Management Feature - Unit & Component Tests", () => {
  const sampleRecord = {
    id: 101,
    computer_id: 11,
    computer_hostname: "DESKTOP-M72R440",
    title: "Quarterly Thermal Paste & Dust Servicing",
    description: "Deep clean CPU heatsink, reapply Arctic MX-4, inspect fan bearings.",
    maintenance_type: "preventive",
    status: "scheduled",
    technician_name: "Sarah Connor",
    scheduled_at: "2026-10-25T09:00:00Z",
    started_at: null,
    completed_at: null,
    work_performed: null,
    notes: "Requires anti-static wrist strap.",
    created_at: "2026-10-19T10:00:00Z",
    updated_at: "2026-10-19T10:00:00Z",
  };

  const sampleCompletedRecord = {
    id: 102,
    computer_id: 12,
    computer_hostname: "LAB-PC-02",
    title: "Replace Failing Secondary HDD",
    description: "Drive SMART logs indicate reallocated sectors > 100.",
    maintenance_type: "hardware",
    status: "completed",
    technician_name: "Alex Murphy",
    scheduled_at: "2026-10-18T14:00:00Z",
    started_at: "2026-10-18T14:15:00Z",
    completed_at: "2026-10-18T15:30:00Z",
    work_performed: "Swapped drive with Crucial MX500 1TB SSD, cloned recovery partition.",
    notes: "System boots 4x faster now.",
    created_at: "2026-10-18T13:00:00Z",
    updated_at: "2026-10-18T15:30:00Z",
  };

  /* ----------------------------------------------------
     1. UTILITY TESTS
  ---------------------------------------------------- */
  describe("Utility Helpers", () => {
    it("formatDateTime formats valid date string correctly", () => {
      const res = formatDateTime("2026-10-25T09:00:00Z");
      expect(res).toContain("Oct");
      expect(res).toContain("2026");
    });

    it("formatDateTime returns fallback on null or empty", () => {
      expect(formatDateTime(null)).toBe("—");
      expect(formatDateTime("")).toBe("—");
    });

    it("formatDateOnly formats date without time", () => {
      const res = formatDateOnly("2026-10-25T09:00:00Z");
      expect(res).toContain("Oct");
      expect(res).toContain("2026");
      expect(formatDate).toBe(formatDateOnly);
    });

    it("getTypeBadgeConfig returns appropriate styles for each type", () => {
      const prev = getTypeBadgeConfig("preventive");
      expect(prev.label).toBe("Preventive");
      expect(prev.color).toBe("#2563EB");

      const emerg = getTypeBadgeConfig("emergency");
      expect(emerg.label).toBe("Emergency");
      expect(emerg.color).toBe("#DC2626");

      const hw = getTypeBadgeConfig("hardware");
      expect(hw.label).toBe("Hardware");

      const sw = getTypeBadgeConfig("software");
      expect(sw.label).toBe("Software");
    });

    it("getStatusBadgeConfig returns appropriate styling for each status", () => {
      const sched = getStatusBadgeConfig("scheduled");
      expect(sched.label).toBe("Scheduled");

      const inProg = getStatusBadgeConfig("in_progress");
      expect(inProg.label).toBe("In Progress");

      const comp = getStatusBadgeConfig("completed");
      expect(comp.label).toBe("Completed");
      expect(comp.color).toBe("#16A34A");

      const canc = getStatusBadgeConfig("cancelled");
      expect(canc.label).toBe("Cancelled");
    });

    it("formatStatusText and formatTypeText handle capitalization and underscores", () => {
      expect(formatStatusText("in_progress")).toBe("In Progress");
      expect(formatStatusText("completed")).toBe("Completed");
      expect(formatTypeText("hardware")).toBe("Hardware");
      expect(formatTypeText("corrective")).toBe("Corrective");
    });

    it("getPaginationItems generates correct pagination arrays", () => {
      expect(getPaginationItems(1, 3)).toEqual([1, 2, 3]);
      const tenPages = getPaginationItems(5, 10);
      expect(tenPages).toContain("...");
      expect(tenPages[tenPages.length - 1]).toBe(10);
    });
  });

  /* ----------------------------------------------------
     2. COMPONENT TESTS
  ---------------------------------------------------- */
  describe("MaintenanceHeader Component", () => {
    it("renders page title and action buttons", () => {
      const html = renderToString(
        <MaintenanceHeader
          onRefresh={() => {}}
          onSchedule={() => {}}
          onExport={() => {}}
          loading={false}
        />
      );

      expect(html).toContain("Maintenance Records");
      expect(html).toContain("Export");
      expect(html).toContain("Schedule Maintenance");
    });
  });

  describe("MaintenanceSummaryCards Component", () => {
    it("renders KPI cards with correct metric values", () => {
      const stats = {
        total: 24,
        scheduled: 7,
        in_progress: 3,
        completed: 14,
        cancelled: 0,
      };

      const html = renderToString(<MaintenanceSummaryCards stats={stats} />);

      expect(html).toContain("Total Records");
      expect(html).toContain("24");
      expect(html).toContain("Scheduled");
      expect(html).toContain("7");
      expect(html).toContain("In Progress");
      expect(html).toContain("3");
      expect(html).toContain("Completed");
      expect(html).toContain("14");
    });
  });

  describe("MaintenanceFilters Component", () => {
    it("renders search input, filter dropdowns, and chips", () => {
      const html = renderToString(
        <MaintenanceFilters
          search="heatsink"
          onSearchChange={() => {}}
          statusFilter="Scheduled"
          onStatusChange={() => {}}
          typeFilter="Preventive"
          onTypeChange={() => {}}
          computerFilter="All Computers"
          onComputerChange={() => {}}
          computers={[{ id: 11, hostname: "DESKTOP-M72R440" }]}
          onRefresh={() => {}}
          onReset={() => {}}
          loading={false}
        />
      );

      expect(html).toContain("heatsink");
      expect(html).toContain("Scheduled");
      expect(html).toContain("Preventive");
      expect(html).toContain("Reset");
    });
  });

  describe("MaintenanceTable Component", () => {
    it("renders maintenance rows with titles, badges, and action buttons", () => {
      const html = renderToString(
        <MaintenanceTable
          records={[sampleRecord, sampleCompletedRecord]}
          selectedRecord={null}
          onSelectRecord={() => {}}
          computerMap={{ 11: { hostname: "DESKTOP-M72R440", ip_address: "192.168.1.100" } }}
          onStatusChange={() => {}}
          onOpenDetails={() => {}}
          onOpenComplete={() => {}}
          onEdit={() => {}}
          onDelete={() => {}}
          loading={false}
        />
      );

      expect(html).toContain("Quarterly Thermal Paste &amp; Dust Servicing");
      expect(html).toContain("Replace Failing Secondary HDD");
      expect(html).toContain("Sarah Connor");
      expect(html).toContain("Alex Murphy");
      expect(html).toContain("#101");
      expect(html).toContain("#102");
    });

    it("renders empty state message when no records exist", () => {
      const html = renderToString(
        <MaintenanceTable
          records={[]}
          selectedRecord={null}
          loading={false}
        />
      );

      expect(html).toContain("No maintenance records found");
    });
  });

  describe("ScheduleMaintenanceModal Component", () => {
    it("returns null when isOpen is false", () => {
      const html = renderToString(
        <ScheduleMaintenanceModal
          isOpen={false}
          onClose={() => {}}
          onSubmit={() => {}}
        />
      );
      expect(html).toBe("");
    });

    it("renders dialog form controls when isOpen is true", () => {
      const html = renderToString(
        <ScheduleMaintenanceModal
          isOpen={true}
          onClose={() => {}}
          computers={[{ id: 11, hostname: "DESKTOP-M72R440" }]}
          onSubmit={() => {}}
        />
      );

      expect(html).toContain("Schedule Maintenance");
      expect(html).toContain("Target Computer");
      expect(html).toContain("Maintenance Type");
      expect(html).toContain("Task Title");
      expect(html).toContain("Assigned Technician");
    });
  });

  describe("CompleteMaintenanceModal Component", () => {
    it("renders work performed input and summary banner", () => {
      const html = renderToString(
        <CompleteMaintenanceModal
          isOpen={true}
          onClose={() => {}}
          record={sampleRecord}
          workPerformed=""
          onWorkPerformedChange={() => {}}
          notes=""
          onNotesChange={() => {}}
          onSubmit={() => {}}
        />
      );

      expect(html).toContain("Complete Maintenance");
      expect(html).toContain("Target Computer:");
      expect(html).toContain("DESKTOP-M72R440");
      expect(html).toContain("Work Performed / Service Summary");
    });
  });

  describe("MaintenanceDetailsModal Component", () => {
    it("renders comprehensive task inspector with metadata and sections", () => {
      const html = renderToString(
        <MaintenanceDetailsModal
          isOpen={true}
          onClose={() => {}}
          record={sampleCompletedRecord}
          onStartMaintenance={() => {}}
          onOpenComplete={() => {}}
        />
      );

      expect(html).toContain("Replace Failing Secondary HDD");
      expect(html).toContain("Alex Murphy");
      expect(html).toContain("Swapped drive with Crucial MX500 1TB SSD");
      expect(html).toContain("System boots 4x faster now");
      expect(html).toContain("Close");
    });
  });
});
