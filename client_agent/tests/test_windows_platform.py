"""
Windows-Specific Integration and Platform Tests (J-06, J-10, J-13 / Stage 6).

Covers real Windows APIs and OS behavior without mocking:
- Real dual 32/64-bit registry enumeration (HKLM\\Software\\...\\Uninstall)
- Real Windows DPAPI Machine-Scope encryption/decryption with entropy
- Real ProgramData path resolution and service identity conventions

SAFETY:
- Marked with `windows_only`.
- Automatically skipped on non-Windows platforms.
- Read-only on the registry; does not modify any system state.
"""

import os
import sys
import pytest

pytestmark = pytest.mark.windows_only


@pytest.fixture(autouse=True)
def guard_windows():
    if sys.platform != "win32":
        pytest.skip("Test requires real Windows operating system.")


def test_real_windows_dual_registry_enumeration():
    """Verify real dual 32-bit and 64-bit registry scanning succeeds on Windows."""
    import winreg
    from modules.software import get_installed_software

    # 1. Directly verify winreg access to the uninstall keys
    keys_checked = 0
    for path in [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
                subkeys, _, _ = winreg.QueryInfoKey(k)
                assert subkeys >= 0
                keys_checked += 1
        except FileNotFoundError:
            # 32-bit uninstall key may not exist on 32-bit Windows, but primary always exists
            pass

    assert keys_checked >= 1

    # 2. Run real collector without mocks
    software = get_installed_software()
    assert isinstance(software, list)
    # A standard Windows OS will have at least several registered applications/runtimes
    assert len(software) > 0

    first_item = software[0]
    assert "name" in first_item
    assert "version" in first_item
    assert "publisher" in first_item
    assert "install_date" in first_item
    assert len(first_item["name"]) > 0


def test_real_windows_dpapi_machine_scope_roundtrip():
    """Verify real Windows DPAPI CryptProtectData/CryptUnprotectData with machine scope & entropy."""
    from core.credentials import is_dpapi_available, dpapi_encrypt, dpapi_decrypt

    assert is_dpapi_available() is True

    plaintext = b"SuperSecretSLMSAgentToken123456789!"
    entropy = b"TestCustomMachineEntropy"

    # Encrypt
    ciphertext = dpapi_encrypt(plaintext, entropy=entropy)
    assert isinstance(ciphertext, bytes)
    assert not ciphertext.startswith(b"MOCK_DPAPI:")
    assert ciphertext != plaintext

    # Decrypt with matching entropy
    decrypted = dpapi_decrypt(ciphertext, entropy=entropy)
    assert decrypted == plaintext

    # Decrypt with incorrect entropy must fail
    wrong_entropy = b"WrongMachineEntropyHere"
    with pytest.raises(Exception):
        dpapi_decrypt(ciphertext, entropy=wrong_entropy)


def test_windows_programdata_path_structure(monkeypatch):
    """Verify production path resolution defaults to %PROGRAMDATA%\\SLMS."""
    # Ensure not in dev mode for this test
    monkeypatch.delenv("SLMS_DEV_MODE", raising=False)
    from paths import CONFIG_FOLDER, LOG_FOLDER, OUTPUT_FOLDER, CACHE_FOLDER

    expected_programdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    expected_root = os.path.join(expected_programdata, "SLMS").lower()

    assert CONFIG_FOLDER.lower().startswith(expected_root)
    assert LOG_FOLDER.lower().startswith(expected_root)
    assert OUTPUT_FOLDER.lower().startswith(expected_root)
    assert CACHE_FOLDER.lower().startswith(expected_root)


def test_windows_service_account_identity():
    """Verify service account conforms to Windows NT SERVICE virtual service account convention."""
    from service.service import DEFAULT_SERVICE_ACCOUNT, SERVICE_NAME

    assert DEFAULT_SERVICE_ACCOUNT == f"NT SERVICE\\{SERVICE_NAME}"
