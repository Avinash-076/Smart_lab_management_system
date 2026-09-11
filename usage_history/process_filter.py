
from pathlib import Path

from process_monitor import get_running_processes


# ============================================================
# CONFIGURATION
# ============================================================

# Processes that are always ignored.
SYSTEM_PROCESSES = {
    # Windows core
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "svchost.exe",

    # Windows shell / infrastructure
    "dwm.exe",
    "fontdrvhost.exe",
    "sihost.exe",
    "taskhostw.exe",
    "runtimebroker.exe",
    "conhost.exe",
    "dllhost.exe",
    "ctfmon.exe",
    "searchhost.exe",
    "searchapp.exe",
    "searchindexer.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "textinputhost.exe",
    "applicationframehost.exe",
    "backgroundtaskhost.exe",
    "wmiprvse.exe",

    # Windows services
    "spoolsv.exe",
    "audiodg.exe",
    "securityhealthservice.exe",
    "securityhealthsystray.exe",
    "trustedinstaller.exe",
    "tiworker.exe",
    "msiexec.exe",

    # Windows widgets / lock screen
    "widgets.exe",
    "widgetservice.exe",
    "lockapp.exe",
}


# ============================================================
# BACKGROUND / SERVICE PROCESS NAMES
#
# These are not applications that the user is actively using.
# ============================================================

BACKGROUND_PROCESSES = {
    # ASUS
    "acpowernotification.exe",
    "armourysocketserver.exe",
    "armouryswagent.exe",
    "asusframework.exe",
    "asusdial.exe",
    "asusdialagent.exe",
    "asusdialservice.exe",
    "asusoledshifter.exe",
    "asusscreenxperthostservice.exe",
    "asusscreenxpertui.exe",

    # Adobe
    "adobecollabsync.exe",
    "armsvc.exe",
    "elevationservice.exe",

    # Android / ADB
    "adb.exe",

    # NVIDIA
    "nvcontainer.exe",
    "nvfvsdksvc.exe",
    "nvrla.exe",
    "nvsphelper64.exe",

    # Intel
    "igcc.exe",
    "intelgraphicssoftware.service.exe",

    # Windows / Microsoft background
    "crossdeviceservice.exe",
    "filecoauth.exe",
    "gameinputredistservice.exe",
    "gamingservices.exe",
    "gamingservicesnet.exe",
    "officeclicktorun.exe",
    "phoneexperiencehost.exe",
    "quickshareservice.exe",
    "rtkuwp.exe",
    "saservice.exe",
    "storedesktopextension.exe",
    "windowspackagemanagerserver.exe",
    "winstore.app.exe",
    "wslservice.exe",

    # ASUS GlideX
    "glidexnearservice.exe",
    "glidexremoteservice.exe",
    "glidexservice.exe",
    "glidexserviceext.exe",

    # Monitoring / diagnostics
    "presentmon.exe",
    "presentmonservice.exe",

    # Other known helpers
    "fvcontainer.exe",
    "fvcontainer.system.exe",
    "promecefpluginhost.exe",

    # Browser crash handlers
    "bravecrashhandler.exe",
    "bravecrashhandler64.exe",

    # Database/service
    "mongod.exe",

    # Docker background service
    "dockerd.exe",
    "docker.exe",

    "asus_framework.exe",
    "elevation_service.exe",
    "msedgewebview2.exe",
    "nvfvsdksvc_x64.exe",
    "nvidia overlay.exe",
    "presentmon_x64.exe",
    "openconsole.exe",
}


# ============================================================
# APPLICATION MAPPINGS
# ============================================================

APPLICATION_MAPPINGS = {

    # --------------------------------------------------------
    # Browsers
    # --------------------------------------------------------

    "chrome.exe": (
        "google_chrome",
        "Google Chrome",
    ),

    "msedge.exe": (
        "microsoft_edge",
        "Microsoft Edge",
    ),

    "firefox.exe": (
        "mozilla_firefox",
        "Mozilla Firefox",
    ),

    "brave.exe": (
        "brave_browser",
        "Brave Browser",
    ),

    "opera.exe": (
        "opera_browser",
        "Opera Browser",
    ),

    "opera_gx.exe": (
        "opera_gx",
        "Opera GX",
    ),

    # --------------------------------------------------------
    # Windows applications
    # --------------------------------------------------------

    "systemsettings.exe": (
        "windows_settings",
        "Settings",
    ),

    "notepad.exe": (
        "notepad",
        "Notepad",
    ),

    "calc.exe": (
        "calculator",
        "Calculator",
    ),

    "mspaint.exe": (
        "paint",
        "Paint",
    ),

    # --------------------------------------------------------
    # Microsoft Office
    # --------------------------------------------------------

    "winword.exe": (
        "microsoft_word",
        "Microsoft Word",
    ),

    "excel.exe": (
        "microsoft_excel",
        "Microsoft Excel",
    ),

    "powerpnt.exe": (
        "microsoft_powerpoint",
        "Microsoft PowerPoint",
    ),

    "outlook.exe": (
        "microsoft_outlook",
        "Microsoft Outlook",
    ),

    # --------------------------------------------------------
    # WPS Office
    # --------------------------------------------------------

    "wps.exe": (
        "wps_office",
        "WPS Office",
    ),

    "wpscloudsvr.exe": (
        "wps_office",
        "WPS Office",
    ),

    "wpp.exe": (
        "wps_office",
        "WPS Office",
    ),

    "et.exe": (
        "wps_office",
        "WPS Office",
    ),

    # --------------------------------------------------------
    # Development
    # --------------------------------------------------------

    "code.exe": (
        "visual_studio_code",
        "Visual Studio Code",
    ),

    "pycharm64.exe": (
        "pycharm",
        "PyCharm",
    ),

    "idea64.exe": (
        "intellij_idea",
        "IntelliJ IDEA",
    ),

    "devenv.exe": (
        "visual_studio",
        "Visual Studio",
    ),

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    "python.exe": (
        "python",
        "Python",
    ),

    "pythonw.exe": (
        "python",
        "Python",
    ),

    # --------------------------------------------------------
    # Media
    # --------------------------------------------------------

    "vlc.exe": (
        "vlc_media_player",
        "VLC Media Player",
    ),

    # --------------------------------------------------------
    # Communication
    # --------------------------------------------------------

    "zoom.exe": (
        "zoom",
        "Zoom",
    ),
}


# ============================================================
# PROCESS GROUPS
# ============================================================

PROCESS_GROUPS = {
    "google_chrome": {
        "chrome.exe",
    },

    "microsoft_edge": {
        "msedge.exe",
    },

    "brave_browser": {
        "brave.exe",
    },

    "mozilla_firefox": {
        "firefox.exe",
    },

    "wps_office": {
        "wps.exe",
        "wpscloudsvr.exe",
        "wpp.exe",
        "et.exe",
    },

    "visual_studio_code": {
        "code.exe",
    },
}


# ============================================================
# USER APPLICATION PATHS
# ============================================================

APPLICATION_PATH_MARKERS = (
    "\\program files\\",
    "\\program files (x86)\\",
    "\\appdata\\local\\programs\\",
    "\\appdata\\local\\",
)


# ============================================================
# PATH NORMALIZATION
# ============================================================

def normalize_process_name(process_name):
    if not process_name:
        return ""

    return process_name.lower().strip()


def normalize_path(path):
    if not path:
        return ""

    return path.lower().replace("/", "\\")


# ============================================================
# APPLICATION PATH CHECK
# ============================================================

def is_likely_application_path(executable_path):

    if not executable_path:
        return False

    path = normalize_path(executable_path)

    # Windows system folders are not user applications.
    system_markers = (
        "\\windows\\system32\\",
        "\\windows\\syswow64\\",
        "\\windows\\winsxs\\",
        "\\windows\\servicing\\",
    )

    if any(marker in path for marker in system_markers):
        return False

    return any(
        marker in path
        for marker in APPLICATION_PATH_MARKERS
    )


# ============================================================
# FALLBACK APPLICATION DETECTION
# ============================================================

def create_fallback_application(process):

    process_name = normalize_process_name(
        process["process_name"]
    )

    executable_path = process.get(
        "executable_path"
    )

    if not executable_path:
        return None

    if not is_likely_application_path(
        executable_path
    ):
        return None

    executable = Path(process_name)

    if executable.suffix.lower() != ".exe":
        return None

    name = executable.stem

    if not name:
        return None

    application_id = (
        "exe_" + name.lower()
    )

    application_name = (
        name.replace("_", " ")
    )

    return {
        "application_id": application_id,
        "application_name": application_name,
    }


# ============================================================
# IDENTIFY APPLICATION
# ============================================================

def identify_application(process):

    process_name = normalize_process_name(
        process["process_name"]
    )

    # --------------------------------------------------------
    # Ignore Windows system process
    # --------------------------------------------------------

    if process_name in SYSTEM_PROCESSES:
        return None

    # --------------------------------------------------------
    # Ignore known background process
    # --------------------------------------------------------

    if process_name in BACKGROUND_PROCESSES:
        return None

    # --------------------------------------------------------
    # Known application
    # --------------------------------------------------------

    known_application = APPLICATION_MAPPINGS.get(
        process_name
    )

    if known_application:

        application_id, application_name = (
            known_application
        )

        return {
            "application_id": application_id,
            "application_name": application_name,
        }

    # --------------------------------------------------------
    # Unknown executable
    # --------------------------------------------------------

    return create_fallback_application(
        process
    )


# ============================================================
# GET USEFUL APPLICATIONS
# ============================================================

def get_useful_applications():

    running_processes = (
        get_running_processes()
    )

    applications = {}

    for process in running_processes:

        application = identify_application(
            process
        )

        if application is None:
            continue

        application_id = (
            application["application_id"]
        )

        # ----------------------------------------------------
        # First process for this application
        # ----------------------------------------------------

        if application_id not in applications:

            applications[application_id] = {
                "application_id": application_id,
                "application_name": (
                    application["application_name"]
                ),
                "process_name": (
                    process["process_name"]
                ),
                "executable_path": (
                    process["executable_path"]
                ),
                "start_time": (
                    process["start_time"]
                ),
            }

        # ----------------------------------------------------
        # Additional process belonging to same application
        # ----------------------------------------------------

        else:

            existing = applications[
                application_id
            ]

            if (
                process["start_time"]
                < existing["start_time"]
            ):

                existing["start_time"] = (
                    process["start_time"]
                )

    return list(
        applications.values()
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    applications = (
        get_useful_applications()
    )

    for application in sorted(
        applications,
        key=lambda item:
            item["application_name"].lower()
    ):

        print(
            f"{application['application_name']} | "
            f"ID={application['application_id']} | "
            f"Process={application['process_name']} | "
            f"Start={application['start_time']}"
        )