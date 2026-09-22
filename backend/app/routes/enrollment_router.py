from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_permission
from app.database import get_db
from app.models.audit_log import AuditResult
from app.models.user import User
from app.schemas.enrollment_schema import (
    EnrollmentKeyResponse,
)
from app.services import (
    audit_service,
    enrollment_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/enrollment-keys",
    tags=["Enrollment"],
)


@router.post(
    "",
    response_model=EnrollmentKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_enrollment_key(
    db: DbSession,
    current_user: User = Depends(
        require_permission("PROVISION_AGENT")
    ),
):

    try:

        record, plaintext = (
            enrollment_service.create_enrollment_key(
                db=db,
                created_by=current_user.id,
            )
        )

        audit_service.log_action(
            db=db,
            action="GENERATE_ENROLLMENT_KEY",
            result=AuditResult.success,
            user_id=current_user.id,
            target_type="enrollment_key",
            target_id=record.id,
        )

    except SQLAlchemyError:
        raise

    return EnrollmentKeyResponse(
        enrollment_key=plaintext,
        expires_at=record.expires_at,
    )