from datetime import datetime

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