"""
SLMS Windows Service Implementation.

Integrates with Windows Service Control Manager (SCM) to run the SLMS Client Agent
automatically on system boot in Session 0, without requiring user login.
Supports START, STOP, SHUTDOWN, status reporting, and automatic failure recovery.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
from typing import Any, Optional

from core.logger import logger
from paths import CACHE_FOLDER, CONFIG_FOLDER, LOG_FOLDER, OUTPUT_FOLDER
from service.lifecycle import ServiceLifecycle, ServiceState

SERVICE_NAME = "SLMSService"
SERVICE_DISPLAY_NAME = "Smart Lab Management System (SLMS) Client Agent"
SERVICE_DESCRIPTION = (
    "Monitors lab workstation health, processes, and software inventory "
    "for the Smart Lab Management System."
)

DEFAULT_SERVICE_ACCOUNT = r"NT SERVICE\SLMSService"

try:
    import win32event
    import win32service
    import win32serviceutil
    HAVE_PYWIN32 = True
    _BaseClass = win32serviceutil.ServiceFramework
except ImportError:
    HAVE_PYWIN32 = False
    _BaseClass = object


class SLMSService(_BaseClass):
    """
    Windows Service host for the SLMS Client Agent.
    Implements Windows Service Control Manager callbacks and coordinates
    the service lifecycle.
    """

    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION

    def __init__(self, args: Any = None):
        if not args:
            args = [SERVICE_NAME]
        if HAVE_PYWIN32 and _BaseClass is not object:
            try:
                super().__init__(args)
            except Exception:
                pass
            try:
                self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            except Exception:
                self.hWaitStop = None
        else:
            self.hWaitStop = None

        self.lifecycle = ServiceLifecycle()
        self.stop_requested = threading.Event()

    def SvcStop(self) -> None:
        """Invoked by Windows SCM when service is requested to STOP."""
        logger.info("Windows Service SCM signal: SERVICE_CONTROL_STOP received.")
        self.ReportServiceStatus(
            win32service.SERVICE_STOP_PENDING if HAVE_PYWIN32 else 0x00000003
        )
        self.stop_requested.set()
        self.lifecycle.stop(timeout=10.0)

        if HAVE_PYWIN32 and self.hWaitStop is not None:
            win32event.SetEvent(self.hWaitStop)

    def SvcShutdown(self) -> None:
        """Invoked by Windows SCM on system shutdown."""
        logger.info("Windows Service SCM signal: SERVICE_CONTROL_SHUTDOWN received.")
        self.SvcStop()

    def SvcDoRun(self) -> None:
        """Main service entry point invoked by Windows SCM when service starts."""
        os.environ["SLMS_SERVICE_MODE"] = "1"
        logger.info("=" * 60)
        logger.info(f"{SERVICE_DISPLAY_NAME} starting under SCM")
        logger.info("=" * 60)

        self.ReportServiceStatus(
            win32service.SERVICE_RUNNING if HAVE_PYWIN32 else 0x00000004
        )

        fatal_error = False
        try:
            self.lifecycle.start()

            # Responsive wait loop checking for SCM stop signal or worker termination
            while not self.stop_requested.is_set():
                if HAVE_PYWIN32 and self.hWaitStop is not None:
                    rc = win32event.WaitForSingleObject(self.hWaitStop, 500)
                    if rc == win32event.WAIT_OBJECT_0:
                        break
                else:
                    if self.stop_requested.wait(timeout=0.5):
                        break

                if self.stop_requested.is_set():
                    break

                # If worker thread died unexpectedly, detect failure
                if self.lifecycle.state == ServiceState.FAILED or (
                    self.lifecycle.worker_finished_event.is_set() and not self.stop_requested.is_set()
                ):
                    if self.lifecycle.state == ServiceState.FAILED or self.lifecycle.last_error is not None:
                        logger.critical(
                            f"FATAL: Service runtime crashed unexpectedly: {self.lifecycle.last_error}"
                        )
                        fatal_error = True
                    else:
                        logger.info("Service runtime stopped cleanly (e.g. workstation not enrolled).")
                    break

        except Exception as e:
            logger.exception(f"Unhandled service exception in SvcDoRun: {e}")
            fatal_error = True
        finally:
            if fatal_error:
                # Unexpected crash: report SERVICE_STOPPED with ERROR_PROCESS_ABORTED (1067)
                # so Windows SCM registers failure and executes configured recovery actions
                self.lifecycle.stop(timeout=2.0)
                win32_exit_code = 1067  # winerror.ERROR_PROCESS_ABORTED
                self.ReportServiceStatus(
                    win32service.SERVICE_STOPPED if HAVE_PYWIN32 else 0x00000001,
                    win32ExitCode=win32_exit_code,
                )
                logger.critical(
                    f"{SERVICE_DISPLAY_NAME} abnormal termination with exit code {win32_exit_code} for SCM recovery."
                )
                os._exit(win32_exit_code)
            else:
                self.lifecycle.stop(timeout=5.0)
                self.ReportServiceStatus(
                    win32service.SERVICE_STOPPED if HAVE_PYWIN32 else 0x00000001,
                    win32ExitCode=0,
                )
                logger.info(f"{SERVICE_DISPLAY_NAME} stopped cleanly.")

    def ReportServiceStatus(self, status: int, win32ExitCode: int = 0, waitHint: int = 0) -> None:
        """Report current service status back to SCM."""
        if HAVE_PYWIN32 and _BaseClass is not object and hasattr(super(), "ReportServiceStatus"):
            try:
                super().ReportServiceStatus(status, win32ExitCode, waitHint)
            except Exception as e:
                logger.debug(f"ReportServiceStatus error: {e}")


# ============================================================================
# Service Recovery & Configuration
# ============================================================================

def get_recovery_command_args(service_name: str = SERVICE_NAME) -> list[str]:
    """
    Return the arguments for sc.exe failure configuration.
    Policy:
    - Reset fail counter after 86400 seconds (24 hours).
    - 1st failure: restart after 5000 ms (5s).
    - 2nd failure: restart after 10000 ms (10s).
    - Subsequent failures: restart after 60000 ms (60s).
    """
    return [
        "sc.exe",
        "failure",
        service_name,
        "reset=",
        "86400",
        "actions=",
        "restart/5000/restart/10000/restart/60000",
    ]


def get_failure_flag_command_args(service_name: str = SERVICE_NAME) -> list[str]:
    """
    Return the arguments for sc.exe failureflag configuration.
    Enables failure actions when the service stops with a non-zero exit code.
    """
    return [
        "sc.exe",
        "failureflag",
        service_name,
        "1",
    ]


def get_privileges_command_args(service_name: str = SERVICE_NAME) -> list[str]:
    """Return sc.exe privs command arguments to declare required privileges."""
    return [
        "sc.exe",
        "privs",
        service_name,
        "SeShutdownPrivilege/SeChangeNotifyPrivilege",
    ]


def assign_account_privileges(account_name: str) -> bool:
    """Assign SeShutdownPrivilege to the service account in LSA."""
    if os.name != "nt" or account_name.lower() == "localsystem":
        return True
    try:
        import win32security
        policy = win32security.LsaOpenPolicy(
            None,
            win32security.POLICY_CREATE_ACCOUNT | win32security.POLICY_LOOKUP_NAMES,
        )
        try:
            sid, _, _ = win32security.LookupAccountName(None, account_name)
            win32security.LsaAddAccountRights(policy, sid, [win32security.SE_SHUTDOWN_NAME])
            logger.info(f"Assigned {win32security.SE_SHUTDOWN_NAME} to {account_name}")
            return True
        finally:
            win32security.LsaClose(policy)
    except Exception as e:
        logger.debug(f"assign_account_privileges notice: {e}")
        return False


def configure_service_folder_permissions(
    service_account: str = DEFAULT_SERVICE_ACCOUNT,
    data_dir: str | None = None,
) -> bool:
    """
    Harden %PROGRAMDATA%\\SLMS folder permissions:
    - Grant Administrators and SYSTEM Full Control (OI)(CI)(F).
    - Grant service account required Modify access with recursive inheritance (OI)(CI)(M).
    - Grant service account Read access to encrypted credential vault if present.
    - Preserves security without granting excessive permissions to Everyone or standard users.
    Logs success or exact failure reason; does not silently suppress errors.
    """
    if os.name != "nt":
        return True

    dev_mode = os.environ.get("SLMS_DEV_MODE", "0").lower() in ("1", "true", "yes")
    if dev_mode:
        logger.info("Skipping production folder ACL hardening in development mode.")
        return True

    from paths import ensure_directories_exist, get_data_dir

    slms_root = data_dir or get_data_dir()
    ensure_directories_exist(slms_root)

    success = True
    try:
        # 1. Grant service account modify access if non-LocalSystem with recursive inheritance
        if service_account and service_account.lower() != "localsystem":
            cmd = ["icacls", slms_root, "/grant", f"{service_account}:(OI)(CI)(M)", "/t"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
            if res.returncode == 0:
                logger.info(f"Granted {service_account} Modify permissions on {slms_root}.")
            else:
                err = res.stderr.strip() or res.stdout.strip()
                logger.warning(f"Failed to grant {service_account} permissions on {slms_root}: {err}")
                success = False

        # 2. Grant service account read access on credential file if present
        config_folder = os.path.join(slms_root, "config")
        cred_file = os.path.join(config_folder, "service_credentials.enc")
        if os.path.isfile(cred_file) and service_account and service_account.lower() != "localsystem":
            cmd_cred = ["icacls", cred_file, "/grant", f"{service_account}:(R)"]
            res_cred = subprocess.run(cmd_cred, capture_output=True, text=True, check=False, timeout=5)
            if res_cred.returncode == 0:
                logger.info(f"Granted {service_account} Read permissions on {cred_file}.")
            else:
                err_cred = res_cred.stderr.strip() or res_cred.stdout.strip()
                logger.warning(f"Failed to grant {service_account} Read on {cred_file}: {err_cred}")
                success = False

        if success:
            logger.info(f"Service folder ACL hardening completed successfully for {slms_root}.")
        return success
    except Exception as e:
        logger.error(f"Error configuring service folder permissions for {slms_root}: {e}")
        return False


def configure_service_recovery(service_name: str = SERVICE_NAME) -> bool:
    """
    Configure Windows SCM automatic recovery actions for unexpected failures.
    Applies both the restart policy and failureflag=1.
    """
    if os.name != "nt":
        return False
    success = True
    try:
        cmd1 = get_recovery_command_args(service_name)
        res1 = subprocess.run(cmd1, capture_output=True, text=True, check=False, timeout=10)
        if res1.returncode == 0:
            logger.info(f"Service recovery policy successfully configured for {service_name}.")
        else:
            logger.warning(f"sc failure output: {res1.stderr.strip() or res1.stdout.strip()}")
            success = False

        cmd2 = get_failure_flag_command_args(service_name)
        res2 = subprocess.run(cmd2, capture_output=True, text=True, check=False, timeout=10)
        if res2.returncode == 0:
            logger.info(f"Service failureflag=1 successfully configured for {service_name}.")
        else:
            logger.warning(f"sc failureflag output: {res2.stderr.strip() or res2.stdout.strip()}")
            success = False

        return success
    except Exception as e:
        logger.warning(f"Failed to configure service recovery policy: {e}")
        return False


def setup_service_environment(service_account: str = DEFAULT_SERVICE_ACCOUNT) -> None:
    """
    Create standard %PROGRAMDATA%\\SLMS directories, configure permissions,
    and migrate legacy outbox if present.
    """
    from paths import ensure_directories_exist
    ensure_directories_exist()
    configure_service_folder_permissions(service_account)
    from core.outbox.migration import migrate_legacy_outbox
    migrate_legacy_outbox()


# ============================================================================
# Service Management Commands
# ============================================================================

def get_service_status(service_name: str = SERVICE_NAME) -> str:
    """
    Query the current status of the service from Windows SCM.
    Returns: 'RUNNING', 'STOPPED', 'START_PENDING', 'STOP_PENDING', 'NOT_INSTALLED', or 'UNKNOWN'.
    """
    if os.name != "nt":
        return "UNKNOWN (Non-Windows)"

    try:
        res = subprocess.run(
            ["sc.exe", "query", service_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        output = res.stdout.upper()
        if "1060" in output or "DOES NOT EXIST" in output:
            return "NOT_INSTALLED"
        if "RUNNING" in output:
            return "RUNNING"
        if "STOPPED" in output:
            return "STOPPED"
        if "START_PENDING" in output:
            return "START_PENDING"
        if "STOP_PENDING" in output:
            return "STOP_PENDING"
        return "UNKNOWN"
    except Exception as e:
        return f"ERROR: {e}"


def get_service_bin_path() -> str:
    """
    Construct the service binary command line.
    When running frozen (compiled executable), points directly to sys.executable
    with the 'run' command without referencing temporary extraction folders (__file__).
    When running in Python development mode, points to python.exe and service.py.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" run'
    python_exe = sys.executable
    script_path = os.path.abspath(__file__)
    return f'"{python_exe}" "{script_path}"'


def get_install_command_args(
    service_name: str = SERVICE_NAME,
    bin_path: str | None = None,
    startup_type: str = "auto",
    display_name: str = SERVICE_DISPLAY_NAME,
    service_account: str = DEFAULT_SERVICE_ACCOUNT,
) -> list[str]:
    """
    Construct the command line arguments for sc.exe create.
    In Windows sc.exe, option keys and values are separate tokens:
    e.g. ['binpath=', bin_path, 'start=', 'auto', 'DisplayName=', display_name, 'obj=', service_account]
    """
    if bin_path is None:
        bin_path = get_service_bin_path()
    start_param = "auto" if startup_type.lower() in ("auto", "automatic") else "demand"
    cmd = [
        "sc.exe",
        "create",
        service_name,
        "binpath=",
        bin_path,
        "start=",
        start_param,
        "DisplayName=",
        display_name,
    ]
    if service_account and service_account.lower() != "localsystem":
        cmd.extend(["obj=", service_account])
    return cmd


def install_service(
    service_account: str = DEFAULT_SERVICE_ACCOUNT,
    startup_type: str = "auto",
) -> bool:
    """
    Install the SLMS Windows Service and configure its failure recovery policy.
    """
    setup_service_environment(service_account)
    bin_path = get_service_bin_path()

    cmd = get_install_command_args(
        service_name=SERVICE_NAME,
        bin_path=bin_path,
        startup_type=startup_type,
        display_name=SERVICE_DISPLAY_NAME,
        service_account=service_account,
    )

    logger.info(f"Creating service {SERVICE_NAME}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
        if res.returncode != 0:
            print(f"Failed to create service: {res.stderr.strip() or res.stdout.strip()}")
            return False

        # Set service description
        subprocess.run(
            ["sc.exe", "description", SERVICE_NAME, SERVICE_DESCRIPTION],
            capture_output=True,
            check=False,
            timeout=5,
        )

        # Configure required privileges via sc privs
        try:
            subprocess.run(
                get_privileges_command_args(SERVICE_NAME),
                capture_output=True,
                check=False,
                timeout=5,
            )
        except Exception:
            pass

        # Assign LSA account rights for SeShutdownPrivilege
        assign_account_privileges(service_account)

        # Grant service account permissions on %PROGRAMDATA%\SLMS
        configure_service_folder_permissions(service_account)

        # Configure recovery policy
        configure_service_recovery(SERVICE_NAME)
        print(f"Service '{SERVICE_NAME}' successfully installed with recovery policy.")
        return True

    except Exception as e:
        print(f"Service installation error: {e}")
        return False



def uninstall_service(service_name: str = SERVICE_NAME) -> bool:
    """Stop and uninstall the SLMS Windows Service."""
    logger.info(f"Uninstalling service {service_name}...")
    try:
        subprocess.run(["sc.exe", "stop", service_name], capture_output=True, check=False, timeout=10)
        res = subprocess.run(["sc.exe", "delete", service_name], capture_output=True, text=True, check=False, timeout=10)
        if res.returncode == 0:
            print(f"Service '{service_name}' uninstalled successfully.")
            return True
        else:
            print(f"Failed to delete service: {res.stderr.strip() or res.stdout.strip()}")
            return False
    except Exception as e:
        print(f"Service uninstallation error: {e}")
        return False


def start_service(service_name: str = SERVICE_NAME) -> bool:
    """Start the service via Windows SCM."""
    try:
        res = subprocess.run(["sc.exe", "start", service_name], capture_output=True, text=True, check=False, timeout=15)
        if res.returncode == 0:
            print(f"Service '{service_name}' start initiated.")
            return True
        else:
            print(f"Failed to start service: {res.stderr.strip() or res.stdout.strip()}")
            return False
    except Exception as e:
        print(f"Service start error: {e}")
        return False


def stop_service(service_name: str = SERVICE_NAME) -> bool:
    """Stop the service via Windows SCM."""
    try:
        res = subprocess.run(["sc.exe", "stop", service_name], capture_output=True, text=True, check=False, timeout=15)
        if res.returncode == 0:
            print(f"Service '{service_name}' stop initiated.")
            return True
        else:
            print(f"Failed to stop service: {res.stderr.strip() or res.stdout.strip()}")
            return False
    except Exception as e:
        print(f"Service stop error: {e}")
        return False


def debug_service() -> None:
    """Run the service directly in console mode for testing and debugging."""
    print("Starting SLMS Service in DEBUG / CONSOLE mode. Press Ctrl+C to stop.")
    os.environ["SLMS_SERVICE_MODE"] = "1"
    svc = SLMSService()
    try:
        svc.lifecycle.start()
        # Keep main thread alive
        while svc.lifecycle.is_healthy():
            threading.Event().wait(1.0)
    except KeyboardInterrupt:
        print("\nStopping debug service...")
    finally:
        svc.SvcStop()
        print("Debug service terminated.")


def run_service() -> None:
    """
    Run the Windows Service under Service Control Manager (SCM).
    Initializes pywin32 servicemanager and starts the Service Control Dispatcher.
    Invoked when the service binary is executed with the 'run' command by SCM.
    """
    if not HAVE_PYWIN32:
        logger.error("pywin32 is not available; cannot start Windows Service.")
        sys.exit(1)

    try:
        import servicemanager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SLMSService)
        servicemanager.StartServiceCtrlDispatcher()
    except Exception as e:
        winerror = getattr(e, "winerror", None)
        if winerror == 1063 or "1063" in str(e):
            print("Note: 'run' is invoked by Windows SCM when starting the service. For interactive debugging, use 'SLMS_Client_Agent.exe debug'.")
            sys.exit(1)
            return
        logger.exception(f"Service dispatcher error: {e}")
        sys.exit(1)


# ============================================================================
# CLI Dispatcher
# ============================================================================

def main():
    # If run via Windows SCM dispatch (e.g. 'run', '--service', '--startup')
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("run", "--service", "--startup"):
        run_service()
        return

    parser = argparse.ArgumentParser(
        description=f"{SERVICE_DISPLAY_NAME} Management Utility",
    )
    subparsers = parser.add_subparsers(dest="command", help="Service command")

    subparsers.add_parser("run", help="Run the Windows service under SCM")
    install_parser = subparsers.add_parser("install", help="Install the Windows service")
    install_parser.add_argument(
        "--account",
        default=DEFAULT_SERVICE_ACCOUNT,
        help=f"Service account (default: {DEFAULT_SERVICE_ACCOUNT})",
    )
    install_parser.add_argument(
        "--startup",
        default="auto",
        choices=["auto", "manual"],
        help="Startup type (default: auto)",
    )

    subparsers.add_parser("uninstall", help="Uninstall the Windows service")
    subparsers.add_parser("start", help="Start the Windows service")
    subparsers.add_parser("stop", help="Stop the Windows service")
    subparsers.add_parser("status", help="Query the Windows service status")
    subparsers.add_parser("debug", help="Run the service in interactive debug mode")

    args = parser.parse_args()

    if args.command == "run":
        run_service()
    elif args.command == "install":
        install_service(service_account=args.account, startup_type=args.startup)
    elif args.command == "uninstall":
        uninstall_service()
    elif args.command == "start":
        start_service()
    elif args.command == "stop":
        stop_service()
    elif args.command == "status":
        status = get_service_status()
        print(f"Service '{SERVICE_NAME}' status: {status}")
    elif args.command == "debug":
        debug_service()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
