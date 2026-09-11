from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator
from datetime import datetime

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

    model_config = ConfigDict(from_attributes=True)

class ComputerUpdate(ComputerBase):
    pass


class ComputerPatch(ComputerSchema):
    hostname: str | None = Field(default=None, min_length=1, max_length=100)
    ip_address: IPvAnyAddress | None = None
    mac_address: str | None = Field(default=None, pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    os_name: str | None = Field(default=None, min_length=1, max_length=100)
    os_version: str | None = Field(default=None, min_length=1, max_length=100)