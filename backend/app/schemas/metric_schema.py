from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class MetricUpload(BaseModel):
    cpu_usage: float = Field(ge=0, le=100)
    ram_usage: float = Field(ge=0, le=100)
    disk_usage: float = Field(ge=0, le=100)
    network_sent: float | None = Field(default=None, ge=0)
    network_received: float | None = Field(default=None, ge=0)

class MetricRespond(BaseModel):
    id: int
    computer_id: int
    cpu_usage: float
    ram_usage: float
    disk_usage: float
    network_sent: float | None 
    network_received: float | None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)