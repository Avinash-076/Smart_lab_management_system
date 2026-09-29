"""
Windows SCM Integration Test (J-10, J-13 / Stage 5).

Validates Windows Service Control Manager interaction:
- Creation
- Query status
- Failure recovery configuration (reset period, restart actions)
- Safe teardown / deletion

SAFETY GUARDS:
1. Marked with both `windows_only` and `integration`.
2. Automatically skipped on non-Windows platforms.
3. Automatically skipped if process is not elevated (administrator).
4. Automatically skipped unless SLMS_RUN_SCM_INTEGRATION=1 is explicitly set in environment.
5. Operates STRICTLY on a dedicated test service ('SLMSTestSCMService') and NEVER
   touches the production 'SLMSService'.
6. Teardown unconditionally stops and deletes the test service.
"""

import ctypes
import os
import subprocess
import sys
import pytest

TEST_SERVICE_NAME = "SLMSTestSCMService"
TEST_DISPLAY_NAME = "SLMS Automated Test SCM Service (Safe Temporary)"


def is_windows() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


pytestmark = [
    pytest.mark.windows_only,
    pytest.mark.integration,
]


@pytest.fixture(autouse=True)
def guard_scm_environment():
    """Ensure tests run only on Windows, with admin privileges, and explicit opt-in."""
    if not is_windows():
        pytest.skip("Windows SCM tests require Windows OS.")
    if not is_admin():
        pytest.skip("Windows SCM tests require elevated Administrator privileges.")
    if os.environ.get("SLMS_RUN_SCM_INTEGRATION") != "1":
        pytest.skip("Set SLMS_RUN_SCM_INTEGRATION=1 to run Windows SCM integration tests.")


@pytest.fixture
def managed_test_service():
    """Fixture ensuring any leftover test service is purged before and after test."""
    # Pre-clean
    subprocess.run(["sc.exe", "stop", TEST_SERVICE_NAME], capture_output=True, check=False)
    subprocess.run(["sc.exe", "delete", TEST_SERVICE_NAME], capture_output=True, check=False)

    yield TEST_SERVICE_NAME

    # Post-clean (always teardown)
    subprocess.run(["sc.exe", "stop", TEST_SERVICE_NAME], capture_output=True, check=False)
    subprocess.run(["sc.exe", "delete", TEST_SERVICE_NAME], capture_output=True, check=False)


def test_scm_service_lifecycle_and_recovery(managed_test_service):
    """
    Validate test service creation, query, recovery configuration, and deletion via SCM.
    """
    service_name = managed_test_service
    python_exe = sys.executable
    dummy_binpath = f'"{python_exe}" -c "import time; time.sleep(1)"'

    # 1. Create service
    create_cmd = [
        "sc.exe",
        "create",
        service_name,
        f"binpath= {dummy_binpath}",
        "start= demand",
        f"DisplayName= {TEST_DISPLAY_NAME}",
    ]
    create_res = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
    assert create_res.returncode == 0, f"Failed to create service: {create_res.stderr or create_res.stdout}"

    try:
        # 2. Query service status
        query_res = subprocess.run(["sc.exe", "query", service_name], capture_output=True, text=True, check=False)
        assert query_res.returncode == 0
        assert "SERVICE_NAME: " + service_name in query_res.stdout
        assert "STOPPED" in query_res.stdout

        # 3. Configure failure recovery (as defined in core/service recovery policy)
        failure_cmd = [
            "sc.exe",
            "failure",
            service_name,
            "reset=",
            "86400",
            "actions=",
            "restart/5000/restart/10000/restart/60000",
        ]
        fail_res = subprocess.run(failure_cmd, capture_output=True, text=True, check=False)
        assert fail_res.returncode == 0, f"Failed to set failure actions: {fail_res.stderr}"

        # 4. Configure failure flag
        flag_cmd = ["sc.exe", "failureflag", service_name, "1"]
        flag_res = subprocess.run(flag_cmd, capture_output=True, text=True, check=False)
        assert flag_res.returncode == 0, f"Failed to set failure flag: {flag_res.stderr}"

        # 5. Query failure configuration
        qfail_res = subprocess.run(["sc.exe", "qfailure", service_name], capture_output=True, text=True, check=False)
        assert qfail_res.returncode == 0
        assert "RESTART" in qfail_res.stdout or "86400" in qfail_res.stdout

    finally:
        # 6. Delete service
        del_res = subprocess.run(["sc.exe", "delete", service_name], capture_output=True, text=True, check=False)
        assert del_res.returncode == 0, f"Failed to delete test service: {del_res.stderr}"
