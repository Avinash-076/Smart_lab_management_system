  import HardwareInfoCard from "./HardwareInfoCard";
import ProcessorCard from "./ProcessorCard";
import MemoryCard from "./MemoryCard";
import StorageCard from "./StorageCard";
import NetworkInfoCard from "./NetworkInfoCard";
import MotherboardCard from "./MotherboardCard";
import GraphicsCard from "./GraphicsCard";
import OtherInfoCard from "./OtherInfoCard";
import "./HardwareInfoTab.css";

export default function HardwareInfoTab({ computer, uptimeText }) {
  const hardware = computer?.hardware || {};

  return (
    <div className="hw-tab-container">
      {/* 2-COLUMN MAIN LAYOUT */}
      <div className="hw-columns-wrapper">
        {/* LEFT COLUMN: Hardware Information + Processor, Memory, Storage */}
        <div className="hw-col-left">
          <HardwareInfoCard computer={computer} hardware={hardware} />

          <div className="hw-left-bottom-grid">
            <ProcessorCard hardware={hardware} />
            <MemoryCard hardware={hardware} />
            <StorageCard hardware={hardware} />
          </div>
        </div>

        {/* RIGHT COLUMN: Network Info, Motherboard + Graphics, Other Information */}
        <div className="hw-col-right">
          <div className="hw-right-top-stack">
            <NetworkInfoCard computer={computer} hardware={hardware} />
            <MotherboardCard hardware={hardware} />
          </div>

          <div className="hw-right-bottom-grid">
            <GraphicsCard hardware={hardware} />
            <OtherInfoCard hardware={hardware} uptimeText={uptimeText} />
          </div>
        </div>
      </div>
    </div>
  );
}
