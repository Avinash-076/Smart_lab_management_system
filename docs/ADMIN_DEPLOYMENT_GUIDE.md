# Smart Lab Management System (SLMS) - Administrator & Deployment Guide

This guide provides end-to-end instructions for Laboratory Technicians, System Administrators, and Faculty to deploy, configure, and maintain the **Smart Lab Management System (SLMS)** in computer laboratories.

---

## 1. Network Topology & System Requirements

### 1.1. Recommended Network Architecture
For maximum reliability, the Host Computer should be assigned a static or DHCP-reserved IP address on the laboratory local area network (LAN):

```
+-------------------------------------------------------------------+
|                        LABORATORY LAN SWITCH                      |
+-------------------------------------------------------------------+
          |                                      |
          |                                      +--- Student PC 01 (192.168.1.101)
          |                                      +--- Student PC 02 (192.168.1.102)
          v                                      +--- Student PC 03 (192.168.1.103)
+-----------------------+                        +--- ...
|   HOST COMPUTER       |                        +--- Student PC 35 (192.168.1.135)
| IP: 192.168.1.100     |
| Port: 18080 (TCP)     |
+-----------------------+
```

### 1.2. Firewall & Port Requirements
* **Port 18080 (TCP Inbound on Host)**: Used for REST API telemetry ingestion and duplex WebSocket channels.
  > *Note: The `SLMS_Host_Setup.exe` installer automatically configures an inbound Windows Firewall rule for Port 18080.*
* **Client Workstations**: No inbound ports required. Student workstations initiate outbound connections to the host IP on port 18080.

### 1.3. Hardware & OS Specifications
* **Host Computer**:
  - Windows 10 or Windows 11 (64-bit).
  - Minimum 4 GB RAM (8 GB recommended for 50+ workstations).
  - 500 MB free disk space.
* **Student Workstations**:
  - Windows 10 or Windows 11 (64-bit).
  - Minimum 2 GB RAM.
  - 100 MB free disk space.

---

## 2. Host Computer Installation & Setup

### Step 2.1: Run the Host Installer
1. Copy `SLMS_Host_Setup.exe` to the Host/Teacher computer.
2. Right-click `SLMS_Host_Setup.exe` and select **Run as administrator**.
3. Choose the installation directory (default: `C:\Program Files\SLMS_Host`).

### Step 2.2: Set Up Administrator Account
During setup, the installer prompts you to create the Master Administrator account:
* **Admin Username**: e.g. `admin`
* **Admin Password**: Minimum 6 characters (e.g. `LabAdmin@2026`)

The installer will:
- Open TCP Port `18080` in Windows Defender Firewall.
- Initialize the secure SQLite database in `%ProgramData%\SLMS_Host`.
- Register and start the `SLMSHostService` Windows Service with automatic failure recovery.
- Create a desktop shortcut for **SLMS Host Dashboard**.

### Step 2.3: Verify Host Service Health
To verify the host service is running properly, open PowerShell as Administrator and run:
```powershell
sc.exe query SLMSHostService
```
You should see:
```text
STATE              : 4  RUNNING
```

To view real-time host service logs:
```powershell
Get-Content -Path "$env:ProgramData\SLMS_Host\logs\service.log" -Tail 20 -Wait
```

### Step 2.4: Launch the Desktop Dashboard
1. Open the **SLMS Host Dashboard** from your desktop or start menu.
2. Log in using your administrator credentials created during setup.
3. The app will appear on screen, and an SLMS icon will appear in your **Windows System Tray** (near the clock).

---

## 3. Workstation Client Agent Deployment

### Step 3.1: Obtain Workstation Enrollment Key
1. In the SLMS Host Dashboard, navigate to **Computers**.
2. Click **Add Workstation** or **Enrollment Keys**.
3. Copy the 64-character enrollment key or note your laboratory default key.

---

### Step 3.2: Method A - Interactive Installation (Single PC)
1. Copy `SLMS_Client_Agent_Setup.exe` to the student computer via USB flash drive or local network share.
2. Right-click and run as Administrator.
3. On the **Server IP or Hostname** page, simply enter the Host computer's IP address:
   ```text
   192.168.1.100
   ```
   *(Port `18080` is detected and attached automatically!)*
4. Paste the **Enrollment Key** when prompted.
5. Click **Install**.
6. The installer automatically enrolls the workstation, encrypts credentials via DPAPI in `%ProgramData%\SLMS\config`, registers `SLMSService`, and launches the notification companion `SLMS_Notifier.exe`.

---

### Step 3.3: Method B - Automated / Silent Deployment (30–60 Lab PCs)
For rolling out across an entire laboratory simultaneously without clicking through wizards:

#### Option 1: PowerShell Network Script
Run this script from an elevated PowerShell prompt on each workstation (or execute remotely via PowerShell Remoting / PDQ Deploy):

```powershell
# Set Host Server IP and Enrollment Key
$HostServerIp = "192.168.1.100"
$EnrollmentKey = "YOUR_64_CHARACTER_ENROLLMENT_KEY_HERE"
$InstallerPath = "\\192.168.1.100\SharedFolder\SLMS_Client_Agent_Setup.exe"

# Execute Silent Unattended Installation
Write-Host "Installing SLMS Client Agent..." -ForegroundColor Cyan
Start-Process -FilePath $InstallerPath -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SERVERURL=http://$($HostServerIp):18080 /KEY=$EnrollmentKey" -Wait

# Verify Windows Service Status
$service = Get-Service -Name "SLMSService" -ErrorAction SilentlyContinue
if ($service -and $service.Status -eq "Running") {
    Write-Host "SLMS Client Agent successfully installed and RUNNING!" -ForegroundColor Green
} else {
    Write-Host "Warning: Service installed but not currently running. Check %ProgramData%\SLMS\logs\agent.log" -ForegroundColor Yellow
}
```

#### Option 2: Command-Line Headless Enrollment
If using the compiled `SLMS_Client_Agent.exe` binary directly:
```cmd
SLMS_Client_Agent.exe enroll --url 192.168.1.100 --key "YOUR_KEY" --force
SLMS_Client_Agent.exe install
SLMS_Client_Agent.exe start
```

---

## 4. System Tray, Alerts & Notification Management

### 4.1. System Tray Controls
When you click the `X` (close) button on the Host Dashboard:
- The window is **hidden** to the System Tray.
- Telemetry recording and real-time monitoring continue running in the background using minimal resources (~20 MB RAM).

To interact with the System Tray:
- **Left-Click / Double-Click**: Instantly unhides and brings the dashboard to the front.
- **Right-Click**:
  - 🖥️ **Show Dashboard**: Restores the window.
  - ❌ **Quit SLMS Host**: Completely exits the dashboard application.

### 4.2. Windows Native Toast Alerts
When a workstation triggers an alert (such as High RAM, High CPU, or Sudden Disconnect):
1. A **Windows Toast Notification** banner slides in at the bottom-right corner of the screen with a chime sound.
2. Clicking the notification restores the dashboard and opens that workstation's hardware details.
3. If you were away from your desk, the notification is safely archived in the **Windows Action Center (Win + N)**.

### 4.3. Configuring Alert Thresholds
To customize when notifications are triggered:
1. In the Dashboard, open **Settings** -> **Monitoring & Alerts**.
2. Adjust the sliders:
   - **RAM Warning / Critical Threshold**: (e.g. Warning at 80%, Critical at 90%).
   - **CPU Critical Threshold**: (e.g. 95% sustained for >30s).
   - **Disk Space Alert**: Trigger when free disk space drops below 10%.
   - **Offline Detection Delay**: (Default: 30 seconds after missed heartbeat).
3. Click **Save Settings**.

---

## 5. Diagnostics, Maintenance & Troubleshooting

### 5.1. Common Issues & Solutions

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| **Client installer reports "Cannot connect to server"** | Host IP incorrect or Firewall blocking port 18080 | 1. Ping the host IP from the student PC (`ping 192.168.1.100`).<br>2. Check if port 18080 is reachable: `Test-NetConnection 192.168.1.100 -Port 18080`.<br>3. Ensure `SLMSHostService` is running on the host. |
| **Workstation shows "Offline" in Dashboard** | Service stopped or network cable unplugged | 1. On student PC, run `sc.exe query SLMSService`.<br>2. Check `%ProgramData%\SLMS\logs\agent.log`.<br>3. Run `net start SLMSService`. |
| **"Insecure HTTP is prohibited in production"** | Testing on public domain without HTTPS | Use the local IP address (e.g. `192.168.1.100`) or set `$env:SLMS_ALLOW_INSECURE_HTTP="1"` for staging environments. |
| **Student running a local FastAPI app gets port collision** | Other software bound to port | SLMS uses dedicated port `18080`. Student projects on `8000`, `3000`, or `5000` will never conflict with SLMS. |

### 5.2. File System Locations

#### On Host Computer:
* **Installation Directory**: `C:\Program Files\SLMS_Host`
* **Database & Logs**: `C:\ProgramData\SLMS_Host`
  - `slms.db` (Primary SQLite Database)
  - `slms.db-wal` (Write-Ahead Log)
  - `logs\service.log` (Host Service Logs)

#### On Student Workstations:
* **Installation Directory**: `C:\Program Files\SLMS`
* **Credentials & Data**: `C:\ProgramData\SLMS`
  - `config\service_credentials.enc` (DPAPI-encrypted machine token)
  - `data\outbox.db` (Durable telemetry queue)
  - `logs\agent.log` (Agent runtime logs)

---

## 6. Uninstallation & Removal

### To Remove Host Software:
1. Open Windows **Settings** -> **Installed Apps**.
2. Select **Smart Lab Management System Host** -> **Uninstall**.
3. The uninstaller will stop `SLMSHostService`, delete the Windows Service registration, remove the firewall rule, and remove application files.

### To Remove Client Agent from Workstations:
1. Open Windows **Installed Apps** -> **Smart Lab Management System Client Agent** -> **Uninstall**.
2. Or run silently via command line:
   ```cmd
   "C:\Program Files\SLMS\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
   ```
