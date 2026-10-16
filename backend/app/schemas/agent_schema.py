from pydantic import BaseModel, ConfigDict
from app.schemas.computer_schema import ComputerCreate
from app.schemas.computer_hardware_schema import ComputerHardwareUpload


class AgentRegisterRequest(BaseModel):
    enrollment_key: str
    device: ComputerCreate
    hardware: ComputerHardwareUpload | None = None

class AgentRegisterResponse(BaseModel):
    computer_id: int
    agent_id: str
    client_secret: str

class AgentAuthRequest(BaseModel):
    agent_id: str
    client_secret: str

class AgentAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    
