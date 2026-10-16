from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator, field_serializer
from datetime import datetime
from app.schemas.computer_hardware_schema import ComputerHardwareResponse

class ComputerSchema(BaseModel):

    @field_validator(
        "hostname",
        "os_name",
        "os_version",
        check_fields=False,
        mode="before",
    )
    @classmethod
    def strip_text_fields(cls, value):
        if isinstance(value, str):
            return value.strip()

        return value

    @field_validator(
        "mac_address",
        check_fields=False,
        mode="before",
    )
    @classmethod
    def normalize_mac_address(cls, value):
        if isinstance(value, str):
            return value.strip().upper()

        return value

    
class ComputerBase(ComputerSchema):
    hostname: str = Field(min_length=1, max_length=100)
    ip_address: IPvAnyAddress
    mac_address: str = Field(pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    os_name: str = Field(min_length=1, max_length=100)
    os_version: str = Field(min_length=1, max_length=100)

    
class ComputerCreate(ComputerBase):
    pass

class ComputerResponse(ComputerBase):
    id: int
    status: str = "offline"
    last_seen: datetime | None = None
    registered_at: datetime | None = None
    hardware: ComputerHardwareResponse | None = None

    @field_serializer("last_seen", when_used="always")
    def serialize_last_seen(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        from datetime import timezone
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat().replace("+00:00", "Z")

    @field_serializer("registered_at", when_used="always")
    def serialize_registered_at(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        from datetime import timezone
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(from_attributes=True)

class ComputerUpdate(ComputerBase):
    pass


class ComputerPatch(ComputerSchema):
    hostname: str | None = Field(default=None, min_length=1, max_length=100)
    ip_address: IPvAnyAddress | None = None
    mac_address: str | None = Field(default=None, pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    os_name: str | None = Field(default=None, min_length=1, max_length=100)
    os_version: str | None = Field(default=None, min_length=1, max_length=100)