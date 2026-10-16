import { describe, it, expect } from "vitest";
import { renderToString } from "react-dom/server";
import HardwareInfoTab from "../features/computers/components/hardware-info/HardwareInfoTab";
import MemoryCard from "../features/computers/components/hardware-info/MemoryCard";
import StorageCard from "../features/computers/components/hardware-info/StorageCard";

describe("HardwareInfoTab and Hardware Cards Regression Tests", () => {
  it("renders '—' for all hardware fields when computer.hardware is missing or null", () => {
    const computer = {
      id: 11,
      hostname: "DESKTOP-M72R440",
      ip_address: "169.254.80.157",
      mac_address: "F8:B4:6A:75:2A:A1",
      os_name: "Windows 10.0.19045",
      hardware: null,
    };

    const html = renderToString(
      <HardwareInfoTab computer={computer} uptimeText="Active" />
    );

    // Hostname and OS from computer root
    expect(html).toContain("DESKTOP-M72R440");
    expect(html).toContain("Windows 10.0.19045");
    expect(html).toContain("169.254.80.157");
    // Hardware fields should render placeholder dashes
    expect(html).toContain("—");
  });

  it("renders full hardware information when computer.hardware is populated", () => {
    const computer = {
      id: 11,
      hostname: "DESKTOP-M72R440",
      ip_address: "169.254.80.157",
      mac_address: "F8:B4:6A:75:2A:A1",
      os_name: "Windows 10.0.19045",
      hardware: {
        manufacturer: "ASUSTeK COMPUTER INC.",
        model: "Vivobook Pro 15",
        serial_number: "SN-987654321",
        system_type: "64-bit operating system, x64-based processor",
        bios_version: "ASUS 305",
        bios_date: "12-01-2024",
        processor_name: "Intel(R) Core(TM) Ultra 7 155H",
        processor_cores: 16,
        processor_threads: 22,
        processor_base_speed: "3.80 GHz",
        processor_max_speed: "4.80 GHz",
        ram_total_gb: 16.0,
        ram_usable_gb: 15.6,
        ram_type: "DDR5",
        ram_speed: "5600 MHz",
        ram_slots_used: 1,
        ram_slots_total: 2,
        storage_drives_count: 1,
        storage_total_gb: 1024.0,
        storage_type: "NVMe SSD",
        storage_health: "Healthy (100%)",
        gpu_name: "NVIDIA GeForce RTX 3050 6GB Laptop GPU",
        gpu_memory_mb: 6144.0,
        gpu_driver_version: "32.0.15.5585",
        subnet_mask: "255.255.0.0",
        default_gateway: "169.254.1.1",
        dns_servers: "1.1.1.1",
        connection_type: "Wi-Fi",
        motherboard_manufacturer: "ASUSTeK COMPUTER INC.",
        motherboard_model: "N6506MJ",
        motherboard_chipset: "Intel Meteor Lake-H",
        motherboard_serial: "MB-123456",
        os_install_date: "15-05-2024",
        last_boot_time: "Today, 03:00 PM",
        power_plan: "Balanced",
      },
    };

    const html = renderToString(
      <HardwareInfoTab computer={computer} uptimeText="Active" />
    );

    expect(html).toContain("ASUSTeK COMPUTER INC.");
    expect(html).toContain("Vivobook Pro 15");
    expect(html).toContain("SN-987654321");
    expect(html).toContain("Intel(R) Core(TM) Ultra 7 155H");
    expect(html).toContain("16");
    expect(html).toContain("22");
    expect(html).toContain("16 GB");
    expect(html).toContain("15.6 GB");
    expect(html).toContain("DDR5");
    expect(html).toContain("5600 MHz");
    expect(html).toContain("1 / 2");
    expect(html).toContain("1024 GB");
    expect(html).toContain("NVMe SSD");
    expect(html).toContain("Healthy (100%)");
    expect(html).toContain("N6506MJ");
    expect(html).toContain("NVIDIA GeForce RTX 3050 6GB Laptop GPU");
    expect(html).toContain("Balanced");
  });

  it("does not mistake numeric 0 values for missing values in MemoryCard and StorageCard", () => {
    const memoryHtml = renderToString(
      <MemoryCard
        hardware={{
          ram_total_gb: 0,
          ram_usable_gb: 0,
          ram_slots_used: 0,
          ram_slots_total: 0,
        }}
      />
    );
    expect(memoryHtml).toContain("0 GB");
    expect(memoryHtml).toContain("0 / 0");

    const storageHtml = renderToString(
      <StorageCard
        hardware={{
          storage_drives_count: 0,
          storage_total_gb: 0,
        }}
      />
    );
    expect(storageHtml).toContain("0 GB");
    expect(storageHtml).toContain("0");
  });
});
