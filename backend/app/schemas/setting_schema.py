from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SettingItemResponse(BaseModel):
    """
    Representation of a single configuration setting.
    """
    key: str = Field(..., description="Unique setting identifier key")
    value: Any = Field(..., description="Parsed typed value (string, int, bool, float)")
    raw_value: str = Field(..., description="String-serialized value as persisted in database")
    category: str = Field(..., description="Configuration grouping category")
    value_type: str = Field(..., description="Value data type: string, int, bool, float")
    description: str | None = Field(None, description="Human-readable description of the setting")
    requires_restart: bool = Field(False, description="Whether changing this setting requires a service restart")
    updated_at: datetime | None = Field(None, description="Timestamp of last modification")
    updated_by: str | None = Field(None, description="Username of operator who last updated the setting")

    model_config = ConfigDict(from_attributes=True)


class SettingsCategoryGroup(BaseModel):
    """
    Settings grouped by functional category.
    """
    category: str
    items: list[SettingItemResponse]


class SettingsListResponse(BaseModel):
    """
    Complete configuration response containing items, category lists, and key-value dictionary.
    """
    items: list[SettingItemResponse]
    categories: list[str]
    settings_map: dict[str, Any]


class SettingsUpdateRequest(BaseModel):
    """
    Payload for batch updating settings.
    Accepts key-value pairs matching recognized setting keys.
    """
    settings: dict[str, Any] = Field(..., description="Map of setting keys to their new values")


class SettingsResetRequest(BaseModel):
    """
    Payload for restoring settings to system defaults.
    """
    keys: list[str] | None = Field(
        None,
        description="Optional list of specific keys to reset. If omitted, all settings are reset.",
    )
