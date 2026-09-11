from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_permission, get_current_user
from app.services import enrollment_service, audit_service 
from app.schemas.enrollment_schema import EnrollmentKeyResponse
from app.models.user import User
from app.models.audit_log import AuditResult

router = APIRouter(prefix="/enrollment-keys", tags=["Enrollment"])
DbSesson = Annotated[Session, Depends(get_db)]

@router.post(
    "",
    response_model=EnrollmentKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_enrollment_key(
    db: DbSesson,
    current_user: User = Depends(require_permission("PROVISION_AGENT")),
):
    record, plaintext= enrollment_service.create_enrollment_key(db, created_by=current_user.id)

    audit_service.log_action(
        db=db,
        action="GENERATE_ENROLLMENT_KEY",
        result=AuditResult.success,
        user_id=current_user.id,
        target_type="enrollment_key",
        target_id=record.id,
    )

    return EnrollmentKeyResponse(enrollment_key=plaintext, expires_at=record.expires_at)
