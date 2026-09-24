from datetime import datetime

import winreg


def _format_install_date(raw_date):
    """
    Convert Windows registry install date from
    YYYYMMDD into YYYY-MM-DD.
    """

    if not raw_date:
        return "Unknown"

    try:
        return datetime.strptime(
            str(raw_date),
            "%Y%m%d",
        ).strftime("%Y-%m-%d")

    except (ValueError, TypeError):
        return str(raw_date)


def _read_value(
    registry_key,
    value_name,
    default="Unknown",
):
    """
    Safely read one Windows registry value.
    """

    try:
        value, _ = winreg.QueryValueEx(
            registry_key,
            value_name,
        )

        if value is None:
            return default

        return value

    except (
        FileNotFoundError,
        OSError,
    ):
        return default


def _scan_registry_path(
    registry_path: str,
    seen: set,
) -> list[dict]:
    """
    Scan one Windows uninstall registry path.
    """

    software_list = []

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            registry_path,
        ) as registry:

            subkey_count = winreg.QueryInfoKey(
                registry
            )[0]

            for index in range(subkey_count):

                try:
                    subkey_name = winreg.EnumKey(
                        registry,
                        index,
                    )

                    with winreg.OpenKey(
                        registry,
                        subkey_name,
                    ) as subkey:

                        name = _read_value(
                            subkey,
                            "DisplayName",
                            "",
                        )

                        if not name:
                            continue

                        version = _read_value(
                            subkey,
                            "DisplayVersion",
                        )

                        publisher = _read_value(
                            subkey,
                            "Publisher",
                        )

                        raw_install_date = _read_value(
                            subkey,
                            "InstallDate",
                            None,
                        )

                        install_date = (
                            _format_install_date(
                                raw_install_date
                            )
                        )

                        identity = (
                            str(name).strip().casefold(),
                            str(version).strip().casefold(),
                        )

                        if identity in seen:
                            continue

                        seen.add(identity)

                        software_list.append(
                            {
                                "name": str(name).strip(),
                                "version": str(version),
                                "publisher": str(publisher),
                                "install_date": install_date,
                            }
                        )

                except (
                    OSError,
                    ValueError,
                    TypeError,
                ):
                    continue

                except Exception:
                    continue

    except (
        OSError,
        FileNotFoundError,
    ):
        pass

    except Exception:
        pass

    return software_list


def get_installed_software() -> list[dict]:
    """
    Collect installed Windows applications.

    Both 64-bit and 32-bit uninstall registry locations
    are scanned.
    """

    software_list = []

    seen: set = set()

    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    for registry_path in registry_paths:

        software_list.extend(
            _scan_registry_path(
                registry_path,
                seen,
            )
        )

    software_list.sort(
        key=lambda item: item["name"].casefold()
    )

    return software_list