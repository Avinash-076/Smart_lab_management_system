import winreg
from datetime import datetime


def _format_install_date(raw_date):
    if not raw_date:
        return "Unknown"
    try:
        # Registry InstallDate is usually YYYYMMDD
        return datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return raw_date  # fall back to whatever string was there


def get_installed_software():
    software_list = []
    seen = set()

    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]

    for path in registry_paths:
        try:
            registry = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            count = winreg.QueryInfoKey(registry)[0]

            for i in range(count):
                try:
                    subkey_name = winreg.EnumKey(registry, i)
                    subkey = winreg.OpenKey(registry, subkey_name)

                    try:
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    except FileNotFoundError:
                        continue

                    try:
                        version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                    except FileNotFoundError:
                        version = "Unknown"

                    try:
                        publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                    except FileNotFoundError:
                        publisher = "Unknown"

                    try:
                        raw_install_date = winreg.QueryValueEx(subkey, "InstallDate")[0]
                    except FileNotFoundError:
                        raw_install_date = None

                    install_date = _format_install_date(raw_install_date)

                    key = (name.strip().lower(), str(version).strip().lower())
                    if key in seen:
                        continue
                    seen.add(key)

                    software_list.append({
                        "name": name,
                        "version": version,
                        "publisher": publisher,
                        "install_date": install_date
                    })

                except Exception:
                    continue

        except Exception:
            continue

    software_list.sort(key=lambda x: x["name"].lower())
    return software_list