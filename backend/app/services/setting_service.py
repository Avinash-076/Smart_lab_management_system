from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting
from app.models.audit_log import AuditResult
from app.schemas.setting_schema import SettingItemResponse, SettingsListResponse
from app.services.audit_service import log_action

# Canonical definition of system settings with metadata, types, and defaults
SETTINGS_CATALOG: dict[str, dict[str, Any]] = {
    "lab_name": {
        "category": "general",
        "value_type": "string",
        "default": "Computer Laboratory",
        "min_len": 1,
        "max_len": 100,
        "description": "Display name of the laboratory facility.",
        "requires_restart": False,
    },
    "lab_location": {
        "category": "general",
        "value_type": "string",
        "default": "Andhra Polytechnic",
        "min_len": 0,
        "max_len": 150,
        "description": "Physical building, campus, or room location.",
        "requires_restart": False,
    },
    "lab_network": {
        "category": "general",
        "value_type": "string",
        "default": "LAN / Ethernet",
        "min_len": 0,
        "max_len": 100,
        "description": "Laboratory network topology or subnet description.",
        "requires_restart": False,
    },
    "cpu_threshold": {
        "category": "monitoring",
        "value_type": "int",
        "default": 85,
        "min_val": 10,
        "max_val": 100,
        "description": "Fleet-wide CPU utilization percentage threshold for alert triggering.",
        "requires_restart": False,
    },
    "ram_threshold": {
        "category": "monitoring",
        "value_type": "int",
        "default": 85,
        "min_val": 10,
        "max_val": 100,
        "description": "Fleet-wide RAM utilization percentage threshold for alert triggering.",
        "requires_restart": False,
    },
    "disk_threshold": {
        "category": "monitoring",
        "value_type": "int",
        "default": 90,
        "min_val": 10,
        "max_val": 100,
        "description": "Fleet-wide Disk utilization percentage threshold for alert triggering.",
        "requires_restart": False,
    },
    "heartbeat_interval": {
        "category": "monitoring",
        "value_type": "int",
        "default": 30,
        "min_val": 5,
        "max_val": 300,
        "description": "Expected client agent heartbeat interval in seconds.",
        "requires_restart": False,
    },
    "disk_alerts": {
        "category": "notifications",
        "value_type": "bool",
        "default": True,
        "description": "Generate in-app notifications when disk usage exceeds threshold.",
        "requires_restart": False,
    },
    "offline_alerts": {
        "category": "notifications",
        "value_type": "bool",
        "default": True,
        "description": "Generate in-app notifications when a computer becomes unresponsive.",
        "requires_restart": False,
    },
    "issue_alerts": {
        "category": "notifications",
        "value_type": "bool",
        "default": True,
        "description": "Generate in-app notifications when a new issue is submitted.",
        "requires_restart": False,
    },
    "software_alerts": {
        "category": "notifications",
        "value_type": "bool",
        "default": False,
        "description": "Generate in-app notifications when unrecognized software is installed.",
        "requires_restart": False,
    },
    "auto_start_agent": {
        "category": "agent",
        "value_type": "bool",
        "default": True,
        "description": "Configure client agent to automatically start on OS boot.",
        "requires_restart": False,
    },
    "collect_processes": {
        "category": "agent",
        "value_type": "bool",
        "default": True,
        "description": "Enable background collection of running process metadata.",
        "requires_restart": False,
    },
    "collect_software": {
        "category": "agent",
        "value_type": "bool",
        "default": True,
        "description": "Enable periodic inventory scans of installed applications.",
        "requires_restart": False,
    },
    "data_retention_days": {
        "category": "agent",
        "value_type": "int",
        "default": 30,
        "min_val": 1,
        "max_val": 365,
        "description": "Retention duration in days for historical telemetry samples.",
        "requires_restart": False,
    },
}

CATEGORIES = ["general", "monitoring", "notifications", "agent"]


def _serialize_value(val: Any, val_type: str) -> str:
    """Serialize typed value to string for database storage."""
    if val_type == "bool":
        return "true" if bool(val) else "false"
    elif val_type in ("int", "float", "string"):
        return str(val)
    elif val_type == "json":
        return json.dumps(val)
    return str(val)


def _parse_value(raw_val: str, val_type: str) -> Any:
    """Parse string from database back to Python typed object."""
    if val_type == "bool":
        return raw_val.strip().lower() in ("true", "1", "yes", "t")
    elif val_type == "int":
        try:
            return int(raw_val.strip())
        except (ValueError, TypeError):
            return 0
    elif val_type == "float":
        try:
            return float(raw_val.strip())
        except (ValueError, TypeError):
            return 0.0
    elif val_type == "json":
        try:
            return json.loads(raw_val)
        except Exception:
            return {}
    return raw_val


def validate_setting_value(key: str, val: Any) -> tuple[Any, str]:
    """
    Validate setting key and value against SETTINGS_CATALOG.
    Returns (parsed_typed_value, serialized_string_value) or raises ValueError.
    """
    if key not in SETTINGS_CATALOG:
        raise ValueError(f"Unknown setting key: '{key}'")

    meta = SETTINGS_CATALOG[key]
    val_type = meta["value_type"]

    if val_type == "string":
        if not isinstance(val, (str, int, float)):
            raise ValueError(f"Setting '{key}' must be a text string")
        s = str(val).strip()
        min_l = meta.get("min_len", 0)
        max_l = meta.get("max_len", 255)
        if len(s) < min_l:
            raise ValueError(f"Setting '{key}' must be at least {min_l} characters")
        if len(s) > max_l:
            raise ValueError(f"Setting '{key}' cannot exceed {max_l} characters")
        return s, s

    elif val_type == "int":
        if isinstance(val, bool):
            raise ValueError(f"Setting '{key}' must be an integer, not a boolean")
        try:
            i = int(val)
        except (ValueError, TypeError):
            raise ValueError(f"Setting '{key}' must be a valid integer")
        min_v = meta.get("min_val")
        max_v = meta.get("max_val")
        if min_v is not None and i < min_v:
            raise ValueError(f"Setting '{key}' must be at least {min_v}")
        if max_v is not None and i > max_v:
            raise ValueError(f"Setting '{key}' cannot exceed {max_v}")
        return i, str(i)

    elif val_type == "float":
        if isinstance(val, bool):
            raise ValueError(f"Setting '{key}' must be a number, not a boolean")
        try:
            f = float(val)
        except (ValueError, TypeError):
            raise ValueError(f"Setting '{key}' must be a valid number")
        min_v = meta.get("min_val")
        max_v = meta.get("max_val")
        if min_v is not None and f < min_v:
            raise ValueError(f"Setting '{key}' must be at least {min_v}")
        if max_v is not None and f > max_v:
            raise ValueError(f"Setting '{key}' cannot exceed {max_v}")
        return f, str(f)

    elif val_type == "bool":
        if isinstance(val, bool):
            b = val
        elif isinstance(val, str):
            if val.lower() in ("true", "1", "yes", "t"):
                b = True
            elif val.lower() in ("false", "0", "no", "f"):
                b = False
            else:
                raise ValueError(f"Setting '{key}' must be a boolean (true/false)")
        elif isinstance(val, int):
            if val in (0, 1):
                b = bool(val)
            else:
                raise ValueError(f"Setting '{key}' must be a boolean (0 or 1)")
        else:
            raise ValueError(f"Setting '{key}' must be a boolean")
        return b, "true" if b else "false"

    return val, str(val)


def seed_default_settings(db: Session) -> None:
    """Ensure all catalog settings exist in the database with their default values."""
    existing = {s.key: s for s in db.scalars(select(AppSetting)).all()}
    now = datetime.now(timezone.utc)
    added = False

    for key, meta in SETTINGS_CATALOG.items():
        if key not in existing:
            raw_def = _serialize_value(meta["default"], meta["value_type"])
            setting = AppSetting(
                key=key,
                value=raw_def,
                category=meta["category"],
                value_type=meta["value_type"],
                description=meta.get("description"),
                requires_restart=meta.get("requires_restart", False),
                updated_at=now,
                updated_by="system",
            )
            db.add(setting)
            added = True

    if added:
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()


def get_all_settings(db: Session) -> SettingsListResponse:
    """Retrieve all application settings, populating missing keys with defaults."""
    db_settings = {s.key: s for s in db.scalars(select(AppSetting)).all()}
    items: list[SettingItemResponse] = []
    settings_map: dict[str, Any] = {}

    for key, meta in SETTINGS_CATALOG.items():
        if key in db_settings:
            db_item = db_settings[key]
            parsed = _parse_value(db_item.value, db_item.value_type)
            item_resp = SettingItemResponse(
                key=db_item.key,
                value=parsed,
                raw_value=db_item.value,
                category=db_item.category,
                value_type=db_item.value_type,
                description=db_item.description or meta.get("description"),
                requires_restart=db_item.requires_restart,
                updated_at=db_item.updated_at,
                updated_by=db_item.updated_by,
            )
        else:
            default_val = meta["default"]
            raw_def = _serialize_value(default_val, meta["value_type"])
            item_resp = SettingItemResponse(
                key=key,
                value=default_val,
                raw_value=raw_def,
                category=meta["category"],
                value_type=meta["value_type"],
                description=meta.get("description"),
                requires_restart=meta.get("requires_restart", False),
                updated_at=None,
                updated_by=None,
            )
        items.append(item_resp)
        settings_map[key] = item_resp.value

    return SettingsListResponse(
        items=items,
        categories=CATEGORIES,
        settings_map=settings_map,
    )


def get_settings_by_category(db: Session, category: str) -> list[SettingItemResponse]:
    """Retrieve settings belonging to a specific category."""
    all_res = get_all_settings(db)
    return [item for item in all_res.items if item.category == category.lower().strip()]


def get_setting_value(db: Session, key: str, fallback: Any = None) -> Any:
    """Fast typed lookup for a single setting."""
    setting = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if setting:
        return _parse_value(setting.value, setting.value_type)
    if key in SETTINGS_CATALOG:
        return SETTINGS_CATALOG[key]["default"]
    return fallback


def update_settings(
    db: Session,
    updates: dict[str, Any],
    actor_id: int | None = None,
    actor_username: str | None = None,
    client_ip: str | None = None,
) -> SettingsListResponse:
    """
    Atomically validate and update multiple settings.
    Rolls back completely if any validation fails.
    Logs an audit event with updated keys.
    """
    if not isinstance(updates, dict):
        raise ValueError("Settings update payload must be a JSON dictionary of key-value pairs")

    if not updates:
        return get_all_settings(db)

    # 1. Validate all keys and values up front
    validated_data: dict[str, tuple[Any, str]] = {}
    for key, val in updates.items():
        validated_data[key] = validate_setting_value(key, val)

    # 2. Persist transactionally
    now = datetime.now(timezone.utc)
    db_settings = {s.key: s for s in db.scalars(select(AppSetting)).all()}

    for key, (typed_val, raw_val) in validated_data.items():
        meta = SETTINGS_CATALOG[key]
        if key in db_settings:
            item = db_settings[key]
            item.value = raw_val
            item.updated_at = now
            item.updated_by = actor_username or "admin"
        else:
            item = AppSetting(
                key=key,
                value=raw_val,
                category=meta["category"],
                value_type=meta["value_type"],
                description=meta.get("description"),
                requires_restart=meta.get("requires_restart", False),
                updated_at=now,
                updated_by=actor_username or "admin",
            )
            db.add(item)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    # 3. Audit trail logging
    changed_keys = sorted(list(validated_data.keys()))
    log_action(
        db=db,
        result=AuditResult.success,
        action=f"SETTINGS_UPDATE: {', '.join(changed_keys[:5])}",
        user_id=actor_id,
        target_type="SETTINGS",
        ip_address=client_ip,
    )

    return get_all_settings(db)


def reset_settings(
    db: Session,
    keys: list[str] | None = None,
    actor_id: int | None = None,
    actor_username: str | None = None,
    client_ip: str | None = None,
) -> SettingsListResponse:
    """
    Reset specified settings (or all settings if keys is None) to catalog defaults.
    """
    target_keys = keys if keys is not None else list(SETTINGS_CATALOG.keys())
    for k in target_keys:
        if k not in SETTINGS_CATALOG:
            raise ValueError(f"Unknown setting key: '{k}'")

    now = datetime.now(timezone.utc)
    db_settings = {s.key: s for s in db.scalars(select(AppSetting)).all()}

    for key in target_keys:
        meta = SETTINGS_CATALOG[key]
        raw_def = _serialize_value(meta["default"], meta["value_type"])
        if key in db_settings:
            item = db_settings[key]
            item.value = raw_def
            item.updated_at = now
            item.updated_by = actor_username or "admin"
        else:
            item = AppSetting(
                key=key,
                value=raw_def,
                category=meta["category"],
                value_type=meta["value_type"],
                description=meta.get("description"),
                requires_restart=meta.get("requires_restart", False),
                updated_at=now,
                updated_by=actor_username or "admin",
            )
            db.add(item)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    log_action(
        db=db,
        result=AuditResult.success,
        action="SETTINGS_RESET",
        user_id=actor_id,
        target_type="SETTINGS",
        ip_address=client_ip,
    )

    return get_all_settings(db)
