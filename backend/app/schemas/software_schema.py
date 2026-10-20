from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SoftwareItem(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    version: str | None = Field(
        default=None,
        max_length=100,
    )

    publisher: str | None = Field(
        default=None,
        max_length=255,
    )

    install_date: str | None = Field(
        default=None,
        max_length=20,
    )

    install_location: str | None = Field(
        default=None,
        max_length=500,
    )

    architecture: str | None = Field(
        default=None,
        max_length=20,
    )


class SoftwareUpload(BaseModel):
    software: list[SoftwareItem] = Field(
        default_factory=list,
        max_length=2000,
    )


class SoftwareResponse(BaseModel):
    id: int
    computer_id: int
    name: str
    version: str | None
    publisher: str | None
    install_date: str | None
    install_location: str | None = None
    architecture: str | None = None
    collected_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class SoftwareCategoryItem(BaseModel):
    category: str
    count: int
    percentage: int


class TopPublisherItem(BaseModel):
    publisher: str
    count: int
    percentage: int


class SoftwareSummaryResponse(BaseModel):
    computer_id: int
    total_installed: int
    recently_installed_7d: int
    potentially_outdated: int | None = None
    last_scan: datetime | None = None
    formatted_last_scan: str = "—"
    categories: list[SoftwareCategoryItem] = Field(default_factory=list)
    top_publishers: list[TopPublisherItem] = Field(default_factory=list)
    available_publishers: list[str] = Field(default_factory=list)
    available_architectures: list[str] = Field(default_factory=list)


class SoftwareComputerInfo(BaseModel):
    id: int
    hostname: str
    ip_address: str | None = None
    os: str | None = None
    status: str | None = "offline"
    install_date: str | None = None


class SoftwareFleetItem(BaseModel):
    id: int
    name: str
    version: str | None = None
    publisher: str | None = None
    install_date: str | None = None
    install_location: str | None = None
    architecture: str | None = None
    collected_at: datetime | None = None
    installed_count: int = 1
    total_computers: int = 1
    os_display: str = "Windows 10/11"
    computers: list[SoftwareComputerInfo] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
    )


class SoftwareOSDistribution(BaseModel):
    os_name: str
    count: int
    percentage: float


class SoftwareFleetSummaryResponse(BaseModel):
    total_software: int
    unique_software: int
    total_computers: int
    computers_with_software: int
    different_publishers: int
    most_common_software: dict[str, Any] | None = None
    top_software: list[dict[str, Any]] = Field(default_factory=list)
    by_os: list[SoftwareOSDistribution] = Field(default_factory=list)
    top_publishers: list[TopPublisherItem] = Field(default_factory=list)
    available_publishers: list[str] = Field(default_factory=list)
    available_os: list[str] = Field(default_factory=list)
    available_architectures: list[str] = Field(default_factory=list)