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
    collected_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )