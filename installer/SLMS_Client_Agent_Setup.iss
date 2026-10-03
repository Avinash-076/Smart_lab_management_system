; ============================================================================
; Smart Lab Management System (SLMS) Client Agent - Windows Installer Setup
; Technology: Inno Setup 6 (x64)
; Target Directory: {autopf}\SLMS (C:\Program Files\SLMS)
; Runtime Data Directory: {commonappdata}\SLMS (C:\ProgramData\SLMS)
; Lifecycle Modes: Fresh Install, Upgrade, Repair, Uninstall, Rollback
; ============================================================================

#define MyAppName "Smart Lab Management System Client Agent"
#define MyAppShortName "SLMS Client Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Smart Lab Management System"
#define MyAppExeName "SLMS_Client_Agent.exe"
#define MyAppId "{{8B96D7F4-429C-4E1E-9FB2-7F36575BC832}"

[Setup]
; Unique application identifier
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SLMS
DefaultGroupName={#MyAppShortName}
DisableDirPage=yes
DisableProgramGroupPage=yes

; Execution Privileges & Architecture
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
MinVersion=10.0

; Output settings
OutputDir=output
OutputBaseFilename=SLMS_Client_Agent_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Uninstaller Configuration
CreateUninstallRegKey=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main executable packaged from compiled PyInstaller distribution
Source: "..\client_agent\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion restartreplace

[Code]
// ===========================================================================
// Phase 4: Lifecycle Modes, Upgrade, Repair, Rollback & Secret Hardening
// ===========================================================================

const
  STATE_CLEAN = 0;           // No EXE, no service, no credentials
  STATE_VALID_INSTALL = 1;   // EXE exists + credentials exist + service registered
  STATE_BROKEN_SERVICE = 2;  // EXE exists + credentials exist, but service missing/broken
  STATE_PARTIAL_INSTALL = 3; // Inconsistent / partial artifacts

  MODE_FRESH_INSTALL = 0;
  MODE_UPGRADE = 1;
  MODE_REPAIR = 2;

var
  ServerUrlPage: TWizardPage;
  ServerUrlEdit: TNewEdit;
  EnrollmentKeyPage: TWizardPage;
  EnrollmentKeyEdit: TNewEdit;
  ConfiguredServerUrl: string;
  ConfiguredEnrollmentKey: string;
  CapturedComputerId: string;
  DetectedState: Integer;
  InstallMode: Integer;
  HasExeBackup: Boolean;
  BackupExePath: string;

// Map exit codes from headless enrollment CLI to user-friendly messages
function GetEnrollmentErrorMessage(ExitCode: Integer): string;
begin
  case ExitCode of
    1: Result := 'Invalid enrollment arguments or empty key specified.';
    2: Result := 'Invalid Server URL format. The server URL must be a valid HTTPS address (e.g. https://slms.lab.edu:8000).';
    3: Result := 'This workstation is already enrolled with SLMS. Use the upgrade or re-enrollment workflow.';
    4: Result := 'The enrollment key is invalid, expired, or has already been used. Please check the key in the SLMS Admin Console.';
    5: Result := 'Duplicate computer registration: A workstation with this hostname or MAC address is already registered in SLMS.';
    6: Result := 'The SLMS server could not be reached. Please check the server address and network connectivity.';
    7: Result := 'TLS/SSL certificate validation failed. Ensure a valid server TLS certificate or enterprise CA bundle is installed.';
    8: Result := 'The SLMS server rejected the enrollment request. Please check server logs and configuration.';
    9: Result := 'An unexpected runtime error occurred during workstation enrollment.';
  else
    Result := 'Workstation enrollment failed with exit code ' + IntToStr(ExitCode) + '.';
  end;
end;

// Stop SLMSService if currently active
procedure StopSLMSService();
var
  ResultCode: Integer;
begin
  Exec('sc.exe', 'stop SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// Remove SLMSService during uninstallation or rollback
procedure UninstallSLMSService();
var
  ResultCode: Integer;
  AgentExePath: string;
begin
  AgentExePath := ExpandConstant('{app}\{#MyAppExeName}');
  if FileExists(AgentExePath) then
  begin
    Exec(AgentExePath, 'uninstall', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end
  else
  begin
    Exec('sc.exe', 'delete SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Deterministic detection of existing installation state
function DetectInstallationState(): Integer;
var
  AppExePath: string;
  CredsPath: string;
  ServiceExists: Boolean;
  ResultCode: Integer;
begin
  AppExePath := ExpandConstant('{autopf}\SLMS\{#MyAppExeName}');
  CredsPath := ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc');

  // Check if SLMSService exists in SCM
  ServiceExists := False;
  if Exec('sc.exe', 'query SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
      ServiceExists := True;
  end;

  if (not FileExists(AppExePath)) and (not FileExists(CredsPath)) and (not ServiceExists) then
  begin
    Result := STATE_CLEAN;
  end
  else if FileExists(AppExePath) and FileExists(CredsPath) and ServiceExists then
  begin
    Result := STATE_VALID_INSTALL;
  end
  else if FileExists(AppExePath) and FileExists(CredsPath) and (not ServiceExists) then
  begin
    Result := STATE_BROKEN_SERVICE;
  end
  else
  begin
    Result := STATE_PARTIAL_INSTALL;
  end;
end;

// Safe Rollback for fresh install failures
procedure RollbackFreshInstallAndAbort(Reason: string);
var
  ResultCode: Integer;
  AgentExePath: string;
  CredFile: string;
begin
  AgentExePath := ExpandConstant('{app}\{#MyAppExeName}');
  CredFile := ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc');

  // 1. Stop and remove service
  Exec('sc.exe', 'stop SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);
  Exec('sc.exe', 'delete SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 2. Remove partial credentials file created during this failed fresh setup
  if FileExists(CredFile) then
    DeleteFile(CredFile);

  // 3. Delete installed executable
  if FileExists(AgentExePath) then
    DeleteFile(AgentExePath);

  // 4. Alert administrator with error details
  MsgBox('Installation Failed' + #13#10#13#10 + Reason, mbError, MB_OK);

  // 5. Abort installation
  Abort();
end;

// Safe Rollback for upgrade / repair failures
procedure RollbackUpgradeAndAbort(Reason: string);
var
  ResultCode: Integer;
  AgentExePath: string;
  Restored: Boolean;
begin
  AgentExePath := ExpandConstant('{app}\{#MyAppExeName}');
  Restored := False;

  // 1. Stop service
  Exec('sc.exe', 'stop SLMSService', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);

  // 2. Restore previous executable from backup if available (Preserves credentials & ProgramData!)
  if HasExeBackup and FileExists(BackupExePath) then
  begin
    if CopyFile(BackupExePath, AgentExePath, False) then
    begin
      Restored := True;
      // Re-reconcile and attempt to start restored service
      Exec(AgentExePath, 'install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Exec(AgentExePath, 'start', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
    DeleteFile(BackupExePath);
    HasExeBackup := False;
  end;

  if Restored then
  begin
    MsgBox('Upgrade Failed' + #13#10#13#10 + Reason + #13#10#13#10 +
           'The previous SLMS Client Agent version has been restored and credentials preserved.',
           mbError, MB_OK);
  end
  else
  begin
    MsgBox('Upgrade Failed' + #13#10#13#10 + Reason + #13#10#13#10 +
           'Existing credentials were preserved, but manual administrator intervention is required.',
           mbError, MB_OK);
  end;

  Abort();
end;

// ===========================================================================
// Custom Wizard Pages Creation
// ===========================================================================

procedure InitializeWizard();
var
  ServerUrlLabel: TLabel;
  ServerUrlHintLabel: TLabel;
  EnrollmentKeyLabel: TLabel;
  EnrollmentKeyHintLabel: TLabel;
begin
  // 1. Server URL Page (Used during Fresh Install)
  ServerUrlPage := CreateCustomPage(
    wpWelcome,
    'SLMS Server Configuration',
    'Specify the network address of the SLMS server.'
  );

  ServerUrlLabel := TLabel.Create(WizardForm);
  ServerUrlLabel.Parent := ServerUrlPage.Surface;
  ServerUrlLabel.Caption := 'Server URL:';
  ServerUrlLabel.Left := 0;
  ServerUrlLabel.Top := ScaleY(10);
  ServerUrlLabel.Width := ServerUrlPage.SurfaceWidth;

  ServerUrlEdit := TNewEdit.Create(WizardForm);
  ServerUrlEdit.Parent := ServerUrlPage.Surface;
  ServerUrlEdit.Text := 'https://';
  ServerUrlEdit.Left := 0;
  ServerUrlEdit.Top := ServerUrlLabel.Top + ServerUrlLabel.Height + ScaleY(6);
  ServerUrlEdit.Width := ServerUrlPage.SurfaceWidth;

  ServerUrlHintLabel := TLabel.Create(WizardForm);
  ServerUrlHintLabel.Parent := ServerUrlPage.Surface;
  ServerUrlHintLabel.Caption :=
    'The server URL must use HTTPS in production (e.g. https://slms.lab.example.edu:8000).' + #13#10 +
    'Plaintext HTTP is prohibited unless development mode is enabled.';
  ServerUrlHintLabel.Left := 0;
  ServerUrlHintLabel.Top := ServerUrlEdit.Top + ServerUrlEdit.Height + ScaleY(12);
  ServerUrlHintLabel.Width := ServerUrlPage.SurfaceWidth;
  ServerUrlHintLabel.WordWrap := True;

  // 2. Workstation Enrollment Key Page (Masked, Used during Fresh Install)
  EnrollmentKeyPage := CreateCustomPage(
    ServerUrlPage.ID,
    'Workstation Enrollment',
    'Enter the workstation enrollment key provided by your SLMS administrator.'
  );

  EnrollmentKeyLabel := TLabel.Create(WizardForm);
  EnrollmentKeyLabel.Parent := EnrollmentKeyPage.Surface;
  EnrollmentKeyLabel.Caption := 'Enrollment Key:';
  EnrollmentKeyLabel.Left := 0;
  EnrollmentKeyLabel.Top := ScaleY(10);
  EnrollmentKeyLabel.Width := EnrollmentKeyPage.SurfaceWidth;

  EnrollmentKeyEdit := TNewEdit.Create(WizardForm);
  EnrollmentKeyEdit.Parent := EnrollmentKeyPage.Surface;
  EnrollmentKeyEdit.PasswordChar := '*'; // Masked input
  EnrollmentKeyEdit.Left := 0;
  EnrollmentKeyEdit.Top := EnrollmentKeyLabel.Top + EnrollmentKeyLabel.Height + ScaleY(6);
  EnrollmentKeyEdit.Width := EnrollmentKeyPage.SurfaceWidth;

  EnrollmentKeyHintLabel := TLabel.Create(WizardForm);
  EnrollmentKeyHintLabel.Parent := EnrollmentKeyPage.Surface;
  EnrollmentKeyHintLabel.Caption :=
    'Enter the workstation enrollment key generated in the SLMS Admin Console.' + #13#10 +
    'This key authorizes this workstation with the backend.' + #13#10 +
    'The key is masked and is never saved in plaintext on disk.';
  EnrollmentKeyHintLabel.Left := 0;
  EnrollmentKeyHintLabel.Top := EnrollmentKeyEdit.Top + EnrollmentKeyEdit.Height + ScaleY(12);
  EnrollmentKeyHintLabel.Width := EnrollmentKeyPage.SurfaceWidth;
  EnrollmentKeyHintLabel.WordWrap := True;
end;

// Skip Server URL and Enrollment Key pages during Upgrade or Repair
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then
  begin
    if (PageID = ServerUrlPage.ID) or (PageID = EnrollmentKeyPage.ID) then
      Result := True;
  end;
end;

// ===========================================================================
// Wizard Validation & Navigation
// ===========================================================================

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Url: string;
  Key: string;
  LowerUrl: string;
begin
  Result := True;

  if CurPageID = ServerUrlPage.ID then
  begin
    Url := Trim(ServerUrlEdit.Text);
    if (Url = '') or (Url = 'https://') or (Url = 'http://') then
    begin
      MsgBox('Please enter the SLMS Server URL.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    LowerUrl := Lowercase(Url);
    if (Pos('http://', LowerUrl) <> 1) and (Pos('https://', LowerUrl) <> 1) then
    begin
      MsgBox('Invalid Server URL scheme. The URL must start with https:// (or http:// for local development).', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    // Check production HTTP rejection
    if (Pos('http://', LowerUrl) = 1) and
       (Pos('http://localhost', LowerUrl) <> 1) and
       (Pos('http://127.0.0.1', LowerUrl) <> 1) and
       (GetEnv('SLMS_ALLOW_INSECURE_HTTP') <> '1') then
    begin
      MsgBox('Insecure HTTP is prohibited in production.' + #13#10#13#10 +
             'Please specify a secure HTTPS URL (e.g. https://slms.lab.example.edu:8000).',
             mbError, MB_OK);
      Result := False;
      Exit;
    end;

    ConfiguredServerUrl := Url;
  end
  else if CurPageID = EnrollmentKeyPage.ID then
  begin
    Key := Trim(EnrollmentKeyEdit.Text);
    if Key = '' then
    begin
      MsgBox('Please enter the Workstation Enrollment Key.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    ConfiguredEnrollmentKey := Key;
  end;
end;

// Summary displayed on Ready to Install page
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := '';
  if InstallMode = MODE_UPGRADE then
  begin
    S := S + 'Operation Mode: Upgrade / Maintenance' + NewLine;
    S := S + Space + 'Existing credentials and telemetry outbox in ProgramData will be preserved.' + NewLine + NewLine;
    S := S + 'Installation Location:' + NewLine;
    S := S + Space + ExpandConstant('{app}') + NewLine;
  end
  else if InstallMode = MODE_REPAIR then
  begin
    S := S + 'Operation Mode: Repair / Service Re-registration' + NewLine;
    S := S + Space + 'Windows Service will be re-registered using existing credentials.' + NewLine + NewLine;
    S := S + 'Installation Location:' + NewLine;
    S := S + Space + ExpandConstant('{app}') + NewLine;
  end
  else
  begin
    S := S + 'Operation Mode: Fresh Installation' + NewLine + NewLine;
    S := S + 'SLMS Server Configuration:' + NewLine;
    S := S + Space + 'Server URL: ' + ConfiguredServerUrl + NewLine + NewLine;
    S := S + 'Workstation Enrollment:' + NewLine;
    S := S + Space + 'Enrollment Key: [Configured]' + NewLine + NewLine;
    S := S + 'Installation Location:' + NewLine;
    S := S + Space + ExpandConstant('{app}') + NewLine;
  end;

  Result := S;
end;

// Update Finished page with status summary
procedure CurPageChanged(CurPageID: Integer);
var
  FinishText: string;
begin
  if CurPageID = wpFinished then
  begin
    if InstallMode = MODE_UPGRADE then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'SLMS Client Agent Upgrade Complete';
      FinishText := 'Smart Lab Management System Client Agent has been successfully upgraded.' + #13#10#13#10 +
                    'Status Summary:' + #13#10 +
                    '  • Windows Service: RUNNING' + #13#10 +
                    '  • Runtime Data: Preserved in ProgramData' + #13#10 +
                    '  • Startup Type: Automatic' + #13#10 +
                    '  • Backend Connection: INITIALIZING' + #13#10#13#10 +
                    'The updated agent will continue monitoring this workstation automatically.';
    end
    else if InstallMode = MODE_REPAIR then
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'SLMS Client Agent Repair Complete';
      FinishText := 'Smart Lab Management System Client Agent has been successfully repaired.' + #13#10#13#10 +
                    'Status Summary:' + #13#10 +
                    '  • Windows Service: RUNNING' + #13#10 +
                    '  • Startup Type: Automatic' + #13#10 +
                    '  • Backend Connection: INITIALIZING' + #13#10#13#10 +
                    'The agent service has been restored and is operating normally.';
    end
    else
    begin
      WizardForm.FinishedHeadingLabel.Caption := 'SLMS Client Agent Installation Complete';
      FinishText := 'Smart Lab Management System Client Agent has been successfully installed and registered.' + #13#10#13#10 +
                    'Status Summary:' + #13#10 +
                    '  • Windows Service: RUNNING' + #13#10 +
                    '  • Startup Type: Automatic' + #13#10;
      if CapturedComputerId <> '' then
        FinishText := FinishText + '  • Computer ID: ' + CapturedComputerId + #13#10;
      FinishText := FinishText + '  • Backend Connection: INITIALIZING' + #13#10#13#10 +
                    'The agent will monitor this workstation and communicate telemetry to the SLMS server automatically.';
    end;
    WizardForm.FinishedLabel.Caption := FinishText;
  end;
end;

// ===========================================================================
// Setup Lifecycle Hooks
// ===========================================================================

function InitializeSetup(): Boolean;
var
  CredsPath: string;
  AppExePath: string;
begin
  // Ensure running on supported 64-bit architecture
  if not Is64BitInstallMode then
  begin
    MsgBox('SLMS Client Agent requires a 64-bit edition of Windows.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  HasExeBackup := False;
  BackupExePath := '';

  // Classify installation state
  DetectedState := DetectInstallationState();

  case DetectedState of
    STATE_CLEAN:
      InstallMode := MODE_FRESH_INSTALL;

    STATE_VALID_INSTALL:
    begin
      InstallMode := MODE_UPGRADE;
    end;

    STATE_BROKEN_SERVICE:
    begin
      InstallMode := MODE_REPAIR;
    end;

    STATE_PARTIAL_INSTALL:
    begin
      CredsPath := ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc');
      AppExePath := ExpandConstant('{autopf}\SLMS\{#MyAppExeName}');

      if FileExists(CredsPath) and (not FileExists(AppExePath)) then
      begin
        // Credentials exist but binary missing: restore binary without re-enrollment
        InstallMode := MODE_UPGRADE;
      end
      else if FileExists(AppExePath) and (not FileExists(CredsPath)) then
      begin
        // Binary exists without credentials: fresh enrollment required
        InstallMode := MODE_FRESH_INSTALL;
      end
      else
      begin
        // Orphaned service without credentials/binary: fresh installation
        InstallMode := MODE_FRESH_INSTALL;
      end;
    end;
  end;

  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AgentExePath: string;
  TempKeyFile: string;
  TempOutFile: string;
  StatusOutFile: string;
  EnrollCmd: string;
  InstallCmd: string;
  AclCmd: string;
  VerifyCmd: string;
  StartCmd: string;
  ResultCode: Integer;
  OutputLines: TArrayOfString;
  I, J: Integer;
  ServiceRunning: Boolean;
  LineText: string;
  CompPos: Integer;
begin
  AgentExePath := ExpandConstant('{app}\{#MyAppExeName}');

  if CurStep = ssInstall then
  begin
    // 1. Stop service prior to file replacement
    StopSLMSService();
    Sleep(1000);

    // 2. If upgrading existing installation, create a temporary backup copy of current executable
    if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then
    begin
      if FileExists(AgentExePath) then
      begin
        BackupExePath := ExpandConstant('{tmp}\SLMS_Client_Agent.exe.bak');
        if CopyFile(AgentExePath, BackupExePath, False) then
          HasExeBackup := True;
      end;
    end;
  end
  else if CurStep = ssPostInstall then
  begin
    // =======================================================================
    // LIFECYCLE BRANCH A: FRESH INSTALLATION (Requires Headless Enrollment)
    // =======================================================================
    if InstallMode = MODE_FRESH_INSTALL then
    begin
      WizardForm.StatusLabel.Caption := 'Registering workstation with SLMS server...';
      TempKeyFile := ExpandConstant('{tmp}\slms_enroll.key');
      TempOutFile := ExpandConstant('{tmp}\slms_enroll_out.log');

      // Write enrollment key to admin-protected temporary key file
      if not SaveStringToFile(TempKeyFile, ConfiguredEnrollmentKey, False) then
      begin
        RollbackFreshInstallAndAbort('Failed to prepare temporary enrollment key file.');
        Exit;
      end;

      // Execute headless enrollment via --key-file (No CLI secret exposure!)
      EnrollCmd := '/c ""' + AgentExePath + '" enroll --url "' + ConfiguredServerUrl + '" --key-file "' + TempKeyFile + '" > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', EnrollCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

      // Temporary secret file cleanup: shred and delete immediately
      SaveStringToFile(TempKeyFile, '0000000000000000000000000000000000000000', False);
      DeleteFile(TempKeyFile);
      ConfiguredEnrollmentKey := ''; // Clear from memory

      if ResultCode <> 0 then
      begin
        if FileExists(TempOutFile) then
          DeleteFile(TempOutFile);
        RollbackFreshInstallAndAbort(GetEnrollmentErrorMessage(ResultCode));
        Exit;
      end;

      // Post-enrollment sanity check: verify service_credentials.enc was created on disk
      if not FileExists(ExpandConstant('{commonappdata}\SLMS\config\service_credentials.enc')) then
      begin
        if FileExists(TempOutFile) then
          DeleteFile(TempOutFile);
        RollbackFreshInstallAndAbort('Enrollment completed but encrypted service credentials file was not created on disk.');
        Exit;
      end;

      // Extract Computer ID from output
      CapturedComputerId := '';
      if FileExists(TempOutFile) then
      begin
        if LoadStringsFromFile(TempOutFile, OutputLines) then
        begin
          for I := 0 to GetArrayLength(OutputLines) - 1 do
          begin
            LineText := OutputLines[I];
            CompPos := Pos('Computer ID:', LineText);
            if CompPos > 0 then
            begin
              CapturedComputerId := Trim(Copy(LineText, CompPos + Length('Computer ID:'), Length(LineText)));
              Break;
            end;
          end;
        end;
        DeleteFile(TempOutFile);
      end;

      // Install Service
      WizardForm.StatusLabel.Caption := 'Installing Windows Service...';
      TempOutFile := ExpandConstant('{tmp}\slms_install_out.log');
      InstallCmd := '/c ""' + AgentExePath + '" install > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', InstallCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackFreshInstallAndAbort('Failed to install SLMS Windows Service via client agent.');
        Exit;
      end;

      // Apply mandatory service credential ACL
      WizardForm.StatusLabel.Caption := 'Configuring service permissions and credential access...';
      AclCmd := '/c ""' + AgentExePath + '" configure-acl > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', AclCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackFreshInstallAndAbort('Failed to configure mandatory service credential permissions for SLMSService.');
        Exit;
      end;

      // Verify credential file accessibility prior to service startup
      WizardForm.StatusLabel.Caption := 'Verifying service credential accessibility...';
      VerifyCmd := '/c ""' + AgentExePath + '" verify-credentials > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', VerifyCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackFreshInstallAndAbort('Service credential verification failed prior to service startup.');
        Exit;
      end;

      // Start Service
      WizardForm.StatusLabel.Caption := 'Starting SLMS Windows Service...';
      StartCmd := '/c ""' + AgentExePath + '" start > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', StartCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackFreshInstallAndAbort('Failed to initiate start of SLMS Windows Service.');
        Exit;
      end;

      // Health Check Polling (Up to 30s)
      WizardForm.StatusLabel.Caption := 'Verifying service health status...';
      ServiceRunning := False;
      StatusOutFile := ExpandConstant('{tmp}\slms_svc_status.log');

      for I := 1 to 30 do
      begin
        Exec('cmd.exe', '/c "sc.exe query SLMSService > "' + StatusOutFile + '" 2>&1"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        if FileExists(StatusOutFile) then
        begin
          if LoadStringsFromFile(StatusOutFile, OutputLines) then
          begin
            for J := 0 to GetArrayLength(OutputLines) - 1 do
            begin
              if (Pos('STATE', OutputLines[J]) > 0) and (Pos('RUNNING', OutputLines[J]) > 0) then
              begin
                ServiceRunning := True;
                Break;
              end;
            end;
          end;
          DeleteFile(StatusOutFile);
        end;

        if ServiceRunning then
          Break;

        Sleep(1000);
      end;

      if not ServiceRunning then
      begin
        RollbackFreshInstallAndAbort('SLMS Windows Service failed to reach RUNNING state within 30 seconds.');
        Exit;
      end;
    end

    // =======================================================================
    // LIFECYCLE BRANCH B: UPGRADE / REPAIR (Preserves Credentials & ProgramData)
    // =======================================================================
    else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then
    begin
      // 1. Reconcile / Reinstall Windows Service (No enrollment!)
      WizardForm.StatusLabel.Caption := 'Reconciling SLMS Windows Service...';
      TempOutFile := ExpandConstant('{tmp}\slms_upgrade_out.log');
      InstallCmd := '/c ""' + AgentExePath + '" install > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', InstallCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackUpgradeAndAbort('Failed to configure SLMS Windows Service during upgrade.');
        Exit;
      end;

      // Apply mandatory service credential ACL
      WizardForm.StatusLabel.Caption := 'Configuring service permissions and credential access...';
      AclCmd := '/c ""' + AgentExePath + '" configure-acl > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', AclCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackUpgradeAndAbort('Failed to configure mandatory service credential permissions during upgrade.');
        Exit;
      end;

      // Verify credential file accessibility prior to service startup
      WizardForm.StatusLabel.Caption := 'Verifying service credential accessibility...';
      VerifyCmd := '/c ""' + AgentExePath + '" verify-credentials > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', VerifyCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackUpgradeAndAbort('Service credential verification failed prior to service startup during upgrade.');
        Exit;
      end;

      // 2. Start Service
      WizardForm.StatusLabel.Caption := 'Starting SLMS Windows Service...';
      StartCmd := '/c ""' + AgentExePath + '" start > "' + TempOutFile + '" 2>&1"';
      Exec('cmd.exe', StartCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      if FileExists(TempOutFile) then
        DeleteFile(TempOutFile);

      if ResultCode <> 0 then
      begin
        RollbackUpgradeAndAbort('Failed to restart SLMS Windows Service during upgrade.');
        Exit;
      end;

      // 3. Health Verification Polling Loop (Up to 30s)
      WizardForm.StatusLabel.Caption := 'Verifying service health status...';
      ServiceRunning := False;
      StatusOutFile := ExpandConstant('{tmp}\slms_svc_status.log');

      for I := 1 to 30 do
      begin
        Exec('cmd.exe', '/c "sc.exe query SLMSService > "' + StatusOutFile + '" 2>&1"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        if FileExists(StatusOutFile) then
        begin
          if LoadStringsFromFile(StatusOutFile, OutputLines) then
          begin
            for J := 0 to GetArrayLength(OutputLines) - 1 do
            begin
              if (Pos('STATE', OutputLines[J]) > 0) and (Pos('RUNNING', OutputLines[J]) > 0) then
              begin
                ServiceRunning := True;
                Break;
              end;
            end;
          end;
          DeleteFile(StatusOutFile);
        end;

        if ServiceRunning then
          Break;

        Sleep(1000);
      end;

      if not ServiceRunning then
      begin
        RollbackUpgradeAndAbort('Upgraded SLMS Windows Service failed to reach RUNNING state within 30 seconds.');
        Exit;
      end;

      // 4. Cleanup temporary backup on confirmed success
      if HasExeBackup and FileExists(BackupExePath) then
      begin
        DeleteFile(BackupExePath);
        HasExeBackup := False;
      end;
    end;
  end;
end;

// ===========================================================================
// Uninstaller Lifecycle Hooks
// ===========================================================================

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // 1. Stop and remove Windows service from SCM before deleting program files
    StopSLMSService();
    UninstallSLMSService();
    // 2. Note: %ProgramData%\SLMS is strictly preserved by default!
  end;
end;
