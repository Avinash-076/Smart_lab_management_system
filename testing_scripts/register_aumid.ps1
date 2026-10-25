# 1. Register com.slms.dashboard in Windows User Notification Settings
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\com.slms.dashboard"
if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}
Set-ItemProperty -Path $regPath -Name "Enabled" -Value 1 -Type DWord
Set-ItemProperty -Path $regPath -Name "ShowInActionCenter" -Value 1 -Type DWord
Write-Host "[OK] Registry Notifications\Settings\com.slms.dashboard created."

# 2. Check if Start Menu shortcut exists and create a registered shortcut in Start Menu Programs
$startMenuDir = "$env:AppData\Microsoft\Windows\Start Menu\Programs\SLMS"
if (-not (Test-Path $startMenuDir)) {
    New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
}

$shortcutPath = "$startMenuDir\SLMS Host Dashboard.lnk"
$targetExe = "D:\PC\slms1\Smart_lab_management_system\frontend\src-tauri\target\release\app.exe"
if (-not (Test-Path $targetExe)) {
    $targetExe = "C:\Program Files\SLMS_Host\SLMS_Host_Dashboard.exe"
}

# 3. Create shortcut using WScript.Shell
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = $targetExe
$sc.WorkingDirectory = Split-Path $targetExe
$sc.Description = "Smart Lab Management System Host Dashboard"
$sc.Save()
Write-Host "[OK] Shortcut created at: $shortcutPath"

# 4. Set AppUserModelID property on the shortcut using Shell.Application PropertyStore
$csharpSource = @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

public class ShellHelper {
    [Guid("886D8EEB-8CF2-4446-8D02-C33547059715"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPropertyStore {
        int GetCount(out uint cProps);
        int GetAt(uint iProp, out PROPERTYKEY pkey);
        int GetValue(ref PROPERTYKEY key, out PROPVARIANT pv);
        int SetValue(ref PROPERTYKEY key, ref PROPVARIANT pv);
        int Commit();
    }

    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    struct PROPERTYKEY {
        public Guid fmtid;
        public uint pid;
    }

    [StructLayout(LayoutKind.Explicit)]
    struct PROPVARIANT {
        [FieldOffset(0)] public ushort vt;
        [FieldOffset(8)] public IntPtr pwszVal;
    }

    static readonly PROPERTYKEY PKEY_AppUserModel_ID = new PROPERTYKEY {
        fmtid = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),
        pid = 5
    };

    public static void SetAumid(string shortcutPath, string aumid) {
        Type shellLinkType = Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"));
        object shellLink = Activator.CreateInstance(shellLinkType);
        ((IPersistFile)shellLink).Load(shortcutPath, 0);

        IPropertyStore propStore = (IPropertyStore)shellLink;
        PROPVARIANT pv = new PROPVARIANT();
        pv.vt = 31; // VT_LPWSTR
        pv.pwszVal = Marshal.StringToCoTaskMemUni(aumid);

        PROPERTYKEY key = PKEY_AppUserModel_ID;
        propStore.SetValue(ref key, ref pv);
        propStore.Commit();

        ((IPersistFile)shellLink).Save(shortcutPath, true);
        Marshal.FreeCoTaskMem(pv.pwszVal);
    }
}
"@

Add-Type -TypeDefinition $csharpSource -ErrorAction SilentlyContinue
[ShellHelper]::SetAumid($shortcutPath, "com.slms.dashboard")
Write-Host "[OK] System.AppUserModel.ID successfully set to 'com.slms.dashboard' on shortcut!"

# 5. Now dispatch the test notification
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>🚨 SLMS Critical Alert - LAB-PC-04</text><text>Workstation LAB-PC-04 has reached 94% RAM usage (15.1 GB / 16 GB)!</text></binding></visual></toast>")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml

[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("com.slms.dashboard").Show($toast)
Write-Host "[SUCCESS] Toast notification successfully dispatched to Windows Action Center!"
