[Setup]
AppName=Smart Lab Management System Host
AppVersion=1.0.0
DefaultDirName={autopf}\SLMS_Host
DefaultGroupName=SLMS Host
OutputDir=output
OutputBaseFilename=SLMS_Host_Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
; 1. Backend Service Files
Source: "..\backend\dist\SLMS_Host_Service\*"; DestDir: "{app}\service"; Flags: ignoreversion recursesubdirs createallsubdirs
; 2. Tauri Desktop Dashboard Executable
Source: "..\frontend\src-tauri\target\release\app.exe"; DestDir: "{app}"; DestName: "SLMS_Host_Dashboard.exe"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\SLMS Host Dashboard"; Filename: "{app}\SLMS_Host_Dashboard.exe"; WorkingDir: "{app}"; AppUserModelID: "com.slms.dashboard"
Name: "{group}\SLMS Host Dashboard"; Filename: "{app}\SLMS_Host_Dashboard.exe"; WorkingDir: "{app}"; AppUserModelID: "com.slms.dashboard"

[Run]
; Open port 18080 in Windows Firewall so lab PCs can connect
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""SLMS Host Service"" dir=in action=allow protocol=TCP localport=18080"; Flags: runhidden
; Provision Administrator credentials entered during setup
Filename: "{app}\service\SLMS_Host_Service.exe"; Parameters: "init-admin ""{code:GetAdminUsername}"" ""{code:GetAdminPassword}"""; Flags: runhidden
; Register the Windows Service
Filename: "{app}\service\SLMS_Host_Service.exe"; Parameters: "--startup auto install"; Flags: runhidden
; Configure Automatic Service Recovery on Failure (restart after 5s)
Filename: "{sys}\sc.exe"; Parameters: "failure SLMSHostService reset= 86400 actions= restart/5000/restart/5000/restart/5000"; Flags: runhidden
; Start the Windows Service immediately
Filename: "net.exe"; Parameters: "start SLMSHostService"; Flags: runhidden
; Optionally launch the Dashboard
Filename: "{app}\SLMS_Host_Dashboard.exe"; Description: "Launch SLMS Host Dashboard"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop and remove the service upon uninstallation
Filename: "net.exe"; Parameters: "stop SLMSHostService"; Flags: runhidden; RunOnceId: "StopSLMSHostService"
Filename: "{app}\service\SLMS_Host_Service.exe"; Parameters: "remove"; Flags: runhidden; RunOnceId: "RemoveSLMSHostService"
; Remove firewall rule
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""SLMS Host Service"""; Flags: runhidden; RunOnceId: "DelFwRule"

[Code]
var
  AdminUserPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  AdminUserPage := CreateInputQueryPage(
    wpSelectDir,
    'Administrator Account Setup',
    'Set up the master administrator account for managing this lab.',
    'Enter the primary username and password for logging into the SLMS Host Dashboard.'
  );
  AdminUserPage.Add('Admin Username:', False);
  AdminUserPage.Add('Admin Password (minimum 6 characters):', True);
  AdminUserPage.Add('Confirm Password:', True);

  AdminUserPage.Values[0] := 'admin';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = AdminUserPage.ID then
  begin
    if Trim(AdminUserPage.Values[0]) = '' then
    begin
      MsgBox('Please enter an Administrator username.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if Length(AdminUserPage.Values[1]) < 6 then
    begin
      MsgBox('Password must be at least 6 characters long.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if AdminUserPage.Values[1] <> AdminUserPage.Values[2] then
    begin
      MsgBox('Passwords do not match. Please re-enter the password.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

function GetAdminUsername(Param: String): String;
begin
  Result := Trim(AdminUserPage.Values[0]);
end;

function GetAdminPassword(Param: String): String;
begin
  Result := AdminUserPage.Values[1];
end;

