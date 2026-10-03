"""
Tests for Inno Setup Installer Script Configuration (Phase 4).

Validates:
1. Script file exists and contains mandatory metadata.
2. Installation state classification (CLEAN, VALID_INSTALL, BROKEN_SERVICE, PARTIAL_INSTALL).
3. Lifecycle modes (FRESH_INSTALL, UPGRADE, REPAIR, UNINSTALL, ROLLBACK).
4. Custom wizard pages (Server URL, Masked Enrollment Key) and page skipping during upgrade/repair.
5. Upgrade preservation of %ProgramData%\\SLMS and service_credentials.enc (no enrollment, no --force).
6. Safe binary replacement and backup mechanism during upgrade.
7. Upgrade rollback restoring previous binary on failure.
8. Fresh install rollback removing partial artifacts on failure.
9. Repair mode service reconciliation without re-enrollment.
10. Uninstaller service removal and runtime data retention policy.
11. Secure key transport mechanism (ephemeral key file with zero CLI exposure and immediate shredding).
12. Absence of hardcoded credentials, keys, or secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import pytest

INSTALLER_DIR = Path(__file__).resolve().parent.parent.parent / "installer"
ISS_FILE = INSTALLER_DIR / "SLMS_Client_Agent_Setup.iss"
SETUP_EXE = INSTALLER_DIR / "output" / "SLMS_Client_Agent_Setup.exe"
DIST_EXE = Path(__file__).resolve().parent.parent / "dist" / "SLMS_Client_Agent.exe"


@pytest.fixture(scope="module")
def iss_content() -> str:
    assert ISS_FILE.is_file(), f"Installer script not found at {ISS_FILE}"
    return ISS_FILE.read_text(encoding="utf-8")


def test_installer_script_metadata(iss_content: str):
    """Test basic installer metadata and target directories."""
    assert 'DefaultDirName={autopf}\\SLMS' in iss_content
    assert 'PrivilegesRequired=admin' in iss_content
    assert 'ArchitecturesInstallIn64BitMode=x64compatible' in iss_content
    assert 'CreateUninstallRegKey=yes' in iss_content
    assert 'OutputBaseFilename=SLMS_Client_Agent_Setup' in iss_content
    assert 'Source: "..\\client_agent\\dist\\{#MyAppExeName}"' in iss_content


def test_installation_state_classification_constants_and_logic(iss_content: str):
    """Verify installation state classification logic covers all 4 states."""
    assert "STATE_CLEAN = 0;" in iss_content
    assert "STATE_VALID_INSTALL = 1;" in iss_content
    assert "STATE_BROKEN_SERVICE = 2;" in iss_content
    assert "STATE_PARTIAL_INSTALL = 3;" in iss_content
    assert "function DetectInstallationState(): Integer;" in iss_content
    assert "MODE_FRESH_INSTALL = 0;" in iss_content
    assert "MODE_UPGRADE = 1;" in iss_content
    assert "MODE_REPAIR = 2;" in iss_content


def test_custom_wizard_pages_and_skipping(iss_content: str):
    """Verify Server URL and Enrollment Key pages exist and are skipped during upgrade/repair."""
    assert "ServerUrlPage := CreateCustomPage(" in iss_content
    assert "EnrollmentKeyPage := CreateCustomPage(" in iss_content
    assert "EnrollmentKeyEdit.PasswordChar := '*';" in iss_content
    assert "function ShouldSkipPage(PageID: Integer): Boolean;" in iss_content
    assert "if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then" in iss_content


def test_fresh_install_lifecycle_sequence(iss_content: str):
    """Verify fresh install executes enrollment before service installation."""
    assert "if InstallMode = MODE_FRESH_INSTALL then" in iss_content
    fresh_block_idx = iss_content.find("if InstallMode = MODE_FRESH_INSTALL then")
    upgrade_block_idx = iss_content.find("else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then")

    fresh_content = iss_content[fresh_block_idx:upgrade_block_idx]
    enroll_idx = fresh_content.find("enroll --url")
    install_idx = fresh_content.find('install > "')
    start_idx = fresh_content.find('start > "')

    assert enroll_idx > 0, "Enrollment command must exist in fresh install block"
    assert install_idx > enroll_idx, "Service install must follow enrollment"
    assert start_idx > install_idx, "Service start must follow service install"


def test_upgrade_lifecycle_preserves_credentials_and_omits_enrollment(iss_content: str):
    """Verify upgrade and repair block does NOT invoke enroll, does NOT use --force, and preserves credentials."""
    upgrade_block_idx = iss_content.find("else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then")
    uninstall_block_idx = iss_content.find("procedure CurUninstallStepChanged")
    upgrade_content = iss_content[upgrade_block_idx:uninstall_block_idx]

    # Ensure enrollment is NEVER called during upgrade/repair
    assert "enroll --url" not in upgrade_content
    assert "--force" not in upgrade_content
    assert "service_credentials.enc" not in upgrade_content, "Upgrade must not modify or reference credentials file for deletion"


def test_safe_binary_replacement_and_backup(iss_content: str):
    """Verify current executable is backed up prior to replacement during upgrade."""
    assert "BackupExePath := ExpandConstant('{tmp}\\SLMS_Client_Agent.exe.bak');" in iss_content
    assert "CopyFile(AgentExePath, BackupExePath, False)" in iss_content
    assert "HasExeBackup := True;" in iss_content


def test_upgrade_rollback_restores_backup(iss_content: str):
    """Verify upgrade rollback restores previous executable from backup."""
    assert "procedure RollbackUpgradeAndAbort" in iss_content
    assert "CopyFile(BackupExePath, AgentExePath, False)" in iss_content
    assert "The previous SLMS Client Agent version has been restored" in iss_content


def test_fresh_install_rollback_cleans_partial_state(iss_content: str):
    """Verify fresh install rollback cleans partial credentials and aborts."""
    assert "procedure RollbackFreshInstallAndAbort" in iss_content
    assert "DeleteFile(CredFile);" in iss_content
    assert "DeleteFile(AgentExePath);" in iss_content
    assert "sc.exe', 'delete SLMSService" in iss_content


def test_repair_mode_reconciles_service_without_enrollment(iss_content: str):
    """Verify repair mode reconciles service without re-enrolling."""
    assert "STATE_BROKEN_SERVICE:\n    begin\n      InstallMode := MODE_REPAIR;" in iss_content or "InstallMode := MODE_REPAIR;" in iss_content
    assert "Operation Mode: Repair / Service Re-registration" in iss_content


def test_uninstaller_removes_service_and_retains_programdata(iss_content: str):
    """Verify uninstaller uninstalls service and leaves ProgramData intact."""
    assert "procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);" in iss_content
    assert "StopSLMSService();" in iss_content
    assert "UninstallSLMSService();" in iss_content
    # Ensure ProgramData is not purged
    assert "{commonappdata}" not in iss_content[iss_content.find("procedure CurUninstallStepChanged"):]


def test_secure_key_transport_and_cleanup(iss_content: str):
    """Verify enrollment key is passed via temporary file, shredded, and never logged."""
    assert "--key \"" not in iss_content
    assert "--key-file" in iss_content
    assert "SaveStringToFile(TempKeyFile, '0000000000000000000000000000000000000000', False);" in iss_content
    assert "DeleteFile(TempKeyFile);" in iss_content
    assert "ConfiguredEnrollmentKey := '';" in iss_content


def test_service_health_polling_bounds(iss_content: str):
    """Verify service health polling loops are bounded at 30 seconds."""
    assert iss_content.count("for I := 1 to 30 do") >= 2  # Once in fresh install, once in upgrade
    assert "sc.exe query SLMSService" in iss_content
    assert "Sleep(1000);" in iss_content


def test_no_hardcoded_secrets(iss_content: str):
    """Verify no real credentials, keys, or passwords exist in the installer script."""
    secret_patterns = [
        r"\bSLMS-[0-9A-Z]{4}-[0-9A-Z]{4}\b",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT pattern
        r"client_secret\s*[:=]\s*['\"][^'\"]+['\"]",
        r"password\s*[:=]\s*['\"][^'\"]+['\"]",
    ]
    for pattern in secret_patterns:
        matches = re.findall(pattern, iss_content, re.IGNORECASE)
        assert len(matches) == 0, f"Found potential secret match: {matches}"


def test_post_enrollment_credentials_verification_in_fresh_install(iss_content: str):
    """Verify fresh install checks for service_credentials.enc existence on disk before installing service."""
    fresh_block_idx = iss_content.find("if InstallMode = MODE_FRESH_INSTALL then")
    upgrade_block_idx = iss_content.find("else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then")
    fresh_content = iss_content[fresh_block_idx:upgrade_block_idx]

    enroll_idx = fresh_content.find("enroll --url")
    check_cred_idx = fresh_content.find("service_credentials.enc")
    install_idx = fresh_content.find('install > "')

    assert check_cred_idx > enroll_idx, "service_credentials.enc check must follow enrollment"
    assert install_idx > check_cred_idx, "Service install must only occur after credentials verification"
    assert "FileExists(ExpandConstant('{commonappdata}\\SLMS\\config\\service_credentials.enc'))" in fresh_content


def test_fresh_install_lifecycle_acl_configuration_sequence(iss_content: str):
    """Verify fresh install applies mandatory ACLs and verifies credentials before starting service."""
    fresh_block_idx = iss_content.find("if InstallMode = MODE_FRESH_INSTALL then")
    upgrade_block_idx = iss_content.find("else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then")
    fresh_content = iss_content[fresh_block_idx:upgrade_block_idx]

    enroll_idx = fresh_content.find("enroll --url")
    install_idx = fresh_content.find('install > "')
    acl_idx = fresh_content.find('configure-acl > "')
    verify_idx = fresh_content.find('verify-credentials > "')
    start_idx = fresh_content.find('start > "')

    assert enroll_idx > 0, "enroll must be present"
    assert install_idx > enroll_idx, "install must follow enroll"
    assert acl_idx > install_idx, "configure-acl must follow install"
    assert verify_idx > acl_idx, "verify-credentials must follow configure-acl"
    assert start_idx > verify_idx, "start must follow verify-credentials"

    assert "Failed to configure mandatory service credential permissions for SLMSService." in fresh_content
    assert "Service credential verification failed prior to service startup." in fresh_content


def test_upgrade_lifecycle_acl_configuration_sequence(iss_content: str):
    """Verify upgrade/repair reconciles ACLs and verifies credentials before restarting service."""
    upgrade_block_idx = iss_content.find("else if (InstallMode = MODE_UPGRADE) or (InstallMode = MODE_REPAIR) then")
    uninstall_block_idx = iss_content.find("procedure CurUninstallStepChanged")
    upgrade_content = iss_content[upgrade_block_idx:uninstall_block_idx]

    install_idx = upgrade_content.find('install > "')
    acl_idx = upgrade_content.find('configure-acl > "')
    verify_idx = upgrade_content.find('verify-credentials > "')
    start_idx = upgrade_content.find('start > "')

    assert install_idx > 0, "install must be present in upgrade block"
    assert acl_idx > install_idx, "configure-acl must follow install"
    assert verify_idx > acl_idx, "verify-credentials must follow configure-acl"
    assert start_idx > verify_idx, "start must follow verify-credentials"

    assert "Failed to configure mandatory service credential permissions during upgrade." in upgrade_content
    assert "Service credential verification failed prior to service startup during upgrade." in upgrade_content


def test_compiled_installer_binary_exists():
    """Verify compiled installer artifact exists and has valid size (> 10MB)."""
    assert SETUP_EXE.is_file(), f"Compiled setup not found at {SETUP_EXE}"
    size = SETUP_EXE.stat().st_size
    assert size > 10 * 1024 * 1024, f"Setup EXE size suspiciously small: {size} bytes"


def test_compiled_installer_artifact_freshness():
    """
    Verify compiled installer artifact is not stale.
    Ensures SETUP_EXE timestamp is >= DIST_EXE timestamp (within standard filesystem tolerance),
    guaranteeing that any newly built client agent executable has been packaged into the installer.
    """
    assert SETUP_EXE.is_file(), f"Compiled setup not found at {SETUP_EXE}"
    if DIST_EXE.is_file():
        setup_mtime = SETUP_EXE.stat().st_mtime
        dist_mtime = DIST_EXE.stat().st_mtime
        # Allow 2 seconds of filesystem tolerance; setup must be at least as fresh as dist EXE
        assert setup_mtime >= (dist_mtime - 2.0), (
            f"Stale installer detected! Setup EXE ({setup_mtime}) is older than "
            f"packaged distribution executable ({dist_mtime}). Inno Setup compilation required."
        )
