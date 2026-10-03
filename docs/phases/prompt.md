Implement automatic Windows environment-variable configuration based on the Server URL entered in the SLMS Inno Setup installer.
Goal
The installer already asks the user for the SLMS Server URL. Make the installer determine whether the URL uses http:// or https:// and configure the Windows environment accordingly so that the installed SLMSService receives the correct transport-security configuration in Windows Session 0.
Required behavior
HTTPS URL
If the user enters:
https://example.com

or any valid https://... URL:
- Do not set SLMS_ALLOW_INSECURE_HTTP.
- Do not automatically set SLMS_DEV_MODE=1.
- Remove stale machine-level SLMS_ALLOW_INSECURE_HTTP and SLMS_DEV_MODE values that were previously created by an older SLMS installation, if appropriate for the installer lifecycle.
- The service must operate normally using HTTPS.
HTTP URL
If the user enters an explicitly permitted HTTP URL such as:
http://169.254.60.157:8000

then:
SLMS_ALLOW_INSECURE_HTTP=1
SLMS_DEV_MODE=1

must be configured as machine-level Windows environment variables, so that NT SERVICE\SLMSService running in Session 0 can read them.
Do not rely on the PowerShell process environment:
$env:SLMS_ALLOW_INSECURE_HTTP="1"

because that environment does not automatically propagate to the installed Windows service.
Preserve existing URL security rules
Do not weaken the current HTTP validation.
The installer must continue to reject HTTP when it is not permitted by the existing project rules.
Preserve the existing behavior that production HTTPS is the normal secure configuration.
Do not simply allow every http:// URL.
Reuse the existing Server URL validation logic where possible instead of creating a second conflicting URL-validation implementation.
Installer lifecycle ordering
Ensure the environment variables are configured before the Windows service is started.
The intended lifecycle should be:
User enters Server URL
        ↓
Validate Server URL
        ↓
Determine HTTP vs HTTPS
        ↓
Configure machine environment variables
        ↓
Install/copy agent
        ↓
Enrollment
        ↓
Create SLMSService
        ↓
Apply mandatory service ACL
        ↓
Verify credentials
        ↓
Start SLMSService
        ↓
Verify RUNNING

The exact existing lifecycle should be inspected before modifying it.
Critical Windows requirement
Because the service runs under Windows Session 0, verify that the machine-level environment variables are actually available to the newly created service.
If Windows requires a service restart/recreation or environment refresh for the service to receive the new values, handle that correctly in the installer lifecycle.
Do not assume that setting the variables in the installer process automatically changes the environment of an already-running service.
Upgrade and repair behavior
Handle existing installations correctly.
HTTPS upgrade:
HTTPS URL
↓
remove stale SLMS insecure-HTTP settings
↓
upgrade/repair service

HTTP upgrade:
HTTP URL
↓
set required machine environment variables
↓
upgrade/repair service

Do not accidentally leave:
SLMS_ALLOW_INSECURE_HTTP=1

enabled after an installation has been changed to HTTPS.
Be careful not to delete unrelated user/system environment variables.
Uninstall behavior
Determine whether the installer created the SLMS machine-level environment variables.
On uninstall, remove only the SLMS environment variables that this installer owns/created. Do not blindly delete values that existed before SLMS installation.
If necessary, record ownership/state so upgrades and uninstall can safely distinguish installer-created variables from pre-existing administrator configuration.
Security requirements
- Never store enrollment keys in environment variables.
- Never store JWTs in environment variables.
- Never store client_secret in environment variables.
- Environment variables should contain only the non-secret configuration flags:
SLMS_DEV_MODE
SLMS_ALLOW_INSECURE_HTTP

- Do not weaken credential ACLs.
- Do not modify the ServiceCredentialStore security model.
- Do not reintroduce Credential Manager/keyring as a workaround.
Important architecture consideration
The current permanent ACL fix must remain intact:
apply_mandatory_service_acls()

must execute regardless of SLMS_DEV_MODE.
Do not reintroduce the previous bug where:
SLMS_DEV_MODE=1

skips mandatory service credential ACL configuration.
Tests
Add/update tests covering:
1. HTTPS URL → insecure HTTP variable is not enabled.
2. HTTP URL → required machine variables are enabled.
3. HTTP URL is still rejected when it violates existing HTTP validation rules.
4. Machine environment variables are configured before service startup.
5. A newly installed service can read the required environment configuration.
6. HTTP installation → service can authenticate and send telemetry.
7. HTTPS installation → service operates normally.
8. HTTP → HTTPS upgrade removes stale insecure HTTP configuration.
9. HTTPS → HTTP upgrade configures the required HTTP settings.
10. Repair preserves the correct URL-dependent configuration.
11. Uninstall removes only installer-owned environment variables.
12. Existing mandatory ACL behavior remains intact.
13. Existing enrollment tests continue passing.
14. Existing outbox/telemetry tests continue passing.
15. Regression test for the original Session 0 problem:
PowerShell temporary environment variables absent
+
machine variables configured by installer
+
SLMSService starts
+
HTTP authentication succeeds
+
telemetry reaches backend

Real-world validation
Test the HTTP case using:
.\SLMS_Client_Agent_Setup.exe

and enter:
http://169.254.60.157:8000

Do not manually set:
$env:SLMS_DEV_MODE="1"
$env:SLMS_ALLOW_INSECURE_HTTP="1"

The installer itself must configure the required machine-level environment variables.
After installation verify:
[Environment]::GetEnvironmentVariable("SLMS_DEV_MODE", "Machine")
[Environment]::GetEnvironmentVariable("SLMS_ALLOW_INSECURE_HTTP", "Machine")

and:
sc.exe query SLMSService

should show:
STATE : 4 RUNNING

Then verify the backend receives requests after registration, not just:
POST /api/agent/register 201 Created

Metrics, authentication, outbox delivery, heartbeat and WebSocket communication should be verified according to the existing architecture.
HTTPS validation
Also test an HTTPS URL and verify that the insecure HTTP variables are not unnecessarily enabled.
Build and regression verification
After implementation:
uv run pytest -q

Then:
uv run pyinstaller --clean --noconfirm SLMS_Client_Agent.spec

Recompile the Inno Setup installer using the existing project ISCC compiler.
Verify that the installer contains the newly built EXE and that the installer timestamp is newer than the EXE.
Run:
git diff --check

Do not modify the backend
This is an installer/client-agent configuration change. Do not modify backend code unless the investigation proves an unavoidable backend dependency.
Final report
Provide:
- exact files changed
- URL-detection implementation
- environment-variable lifecycle
- HTTP behavior
- HTTPS behavior
- upgrade behavior
- repair behavior
- uninstall behavior
- security considerations
- tests added/updated
- full test result
- PyInstaller result
- Inno Setup result
- final installer path
- final installer SHA-256
- any remaining limitations.
Most important: the user should only need to enter the Server URL. The installer must automatically configure the environment required by the installed Windows service based on whether that URL is HTTP or HTTPS. The user must not have to manually set PowerShell environment variables.