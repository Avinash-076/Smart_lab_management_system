from datetime import datetime
from pydantic import BaseModel

class EnrollmentKeyResponse(BaseModel):
    enrollment_key: str
    expires_at: datetime