"""
SLMS Host Windows Service Runner
Runs the FastAPI application under Windows Service Control Manager.
"""
import sys
import os

# Prevent NoneType AttributeError when running in Windows GUI/Service mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import multiprocessing
import threading
import uvicorn
import win32serviceutil
import win32service
import win32event
import win32timezone
import win32api
import win32con
import servicemanager

# Configure persistent database directory in %ProgramData%\SLMS_Host before importing FastAPI app
program_data = os.environ.get("ProgramData", r"C:\ProgramData")
data_dir = os.path.join(program_data, "SLMS_Host")
os.makedirs(data_dir, exist_ok=True)
os.environ["SLMS_DATA_DIR"] = data_dir

db_path = os.path.join(data_dir, "slms.db").replace(os.sep, "/")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

if not os.environ.get("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "slms-secure-lab-secret-key-2026"

import passlib.handlers.bcrypt
from app.main import app 

class SLMSHostService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SLMSHostService"
    _svc_display_name_ = "SLMS Host Management Service"
    _svc_description_ = "Smart Lab Management System central backend and telemetry coordinator."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.server_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.server:
            self.server.should_exit = True
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Configure persistent database directory in %ProgramData%\SLMS_Host
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        data_dir = os.path.join(program_data, "SLMS_Host")
        os.makedirs(data_dir, exist_ok=True)
        os.environ["SLMS_DATA_DIR"] = data_dir

        # Run uvicorn server bound to all network interfaces on port 8000
        # log_config=None is required because Windows Service has no console stdout
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_config=None,
            access_log=False
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(target=self.server.run, daemon=True)
        self.server_thread.start()

        # Tell Windows SCM that the service is now fully RUNNING
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)

        # Wait until Windows SCM signals a stop
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

        # Report stopped to Windows SCM
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)


def init_admin(username: str, password: str):
    """Provisions or updates the initial Administrator user credentials."""
    from app.database import Base, engine, SessionLocal
    from app.services.role_service import seed_default_roles_and_permissions
    from app.services.setting_service import seed_default_settings
    from app.models.user import User
    from app.models.role import Role
    from app.auth import hash_password
    from sqlalchemy import select

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_default_roles_and_permissions(db)
        seed_default_settings(db)

        admin_role = db.scalar(select(Role).where(Role.name == "Administrator"))
        existing_user = db.scalar(select(User).where(User.username == username))

        if existing_user:
            existing_user.password_hash = hash_password(password)
            existing_user.role_id = admin_role.id if admin_role else 1
            existing_user.is_active = True
        else:
            new_admin = User(
                username=username,
                email=f"{username}@slms.local",
                full_name="System Administrator",
                password_hash=hash_password(password),
                role_id=admin_role.id if admin_role else 1,
                is_active=True,
            )
            db.add(new_admin)

        db.commit()
    print(f"Admin user '{username}' configured successfully.")
    sys.exit(0)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) >= 4 and sys.argv[1].lower() == "init-admin":
        init_admin(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SLMSHostService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SLMSHostService)
