from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.database import get_db
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.schemas.computer_schema import (
    ComputerCreate,
    ComputerResponse,
    ComputerUpdate,
    ComputerPatch,
)
from app.schemas.software_schema import SoftwareResponse
from app.schemas.process_schema import ProcessResponse
from app.schemas.usage_schema import UsageSessionResponse
from app.schemas.issue_schema import IssueResponse
from app.schemas.maintenance_schema import MaintenanceResponse
from app.schemas.notification_schema import NotificationResponse
from app.models.issue import IssueStatus, IssueSeverity
from app.models.maintenance import MaintenanceStatus, MaintenanceType
from app.models.notification import NotificationSeverity
from app.services import (
    audit_service,
    computer_service,
    issue_service,
    maintenance_service,
    notification_service,
    process_service,
    software_service,
    usage_service,
)
from app.auth import get_current_user, require_permission, get_current_agent
from app.models.audit_log import AuditResult

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(
    prefix="/clients",
    tags=["Computers"],
)

# routes from here

@router.get(
    "",
    response_model=list[ComputerResponse],
)
def get_all_computers(
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    status: str | None = None,
):
    return computer_service.get_all_computers(db, status=status)


@router.get(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def get_computer(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return computer


@router.get(
    "/{computer_id}/software",
    response_model=list[SoftwareResponse],
)
def get_computer_software(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return software_service.get_software_for_computer(
        db=db,
        computer_id=computer_id,
    )


@router.get(
    "/{computer_id}/processes",
    response_model=list[ProcessResponse],
)
def get_computer_processes(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return process_service.get_processes_for_computer(
        db=db,
        computer_id=computer_id,
    )


def parse_query_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    cleaned = val.strip().replace(" ", "+")
    if cleaned.endswith("Z") or cleaned.endswith("z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {val}. Expected ISO-8601 string.",
        )


@router.get(
    "/{computer_id}/usage",
    response_model=list[UsageSessionResponse],
)
def get_computer_usage(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    limit: int = 100,
    offset: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    parsed_start = parse_query_datetime(start_time)
    parsed_end = parse_query_datetime(end_time)

    return usage_service.get_usage_for_computer(
        db=db,
        computer_id=computer_id,
        limit=limit,
        offset=offset,
        start_time=parsed_start,
        end_time=parsed_end,
    )


@router.get(
    "/{computer_id}/issues",
    response_model=list[IssueResponse],
)
def get_computer_issues(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    issue_status: IssueStatus | None = Query(
        default=None,
        alias="status",
    ),
    severity: IssueSeverity | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return issue_service.get_issues(
        db=db,
        computer_id=computer_id,
        status=issue_status,
        severity=severity,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{computer_id}/maintenance",
    response_model=list[MaintenanceResponse],
)
def get_computer_maintenance(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    maintenance_status: MaintenanceStatus | None = Query(
        default=None,
        alias="status",
    ),
    maintenance_type: MaintenanceType | None = Query(
        default=None,
        alias="type",
    ),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    return maintenance_service.get_maintenance_records(
        db=db,
        computer_id=computer_id,
        maintenance_status=maintenance_status,
        maintenance_type=maintenance_type,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{computer_id}/notifications",
    response_model=list[NotificationResponse],
)
def get_computer_notifications(
    computer_id: int,
    db: DbSession,
    _user=Depends(require_permission("VIEW_COMPUTERS")),
    category: str | None = None,
    severity: NotificationSeverity | None = None,
    unread_only: bool = Query(default=False),
    is_read: bool | None = Query(default=None),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    computer = computer_service.get_computer_by_id(db, computer_id)

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    filter_is_read = is_read
    if unread_only:
        filter_is_read = False

    return notification_service.get_notifications(
        db=db,
        computer_id=computer_id,
        category=category,
        severity=severity,
        is_read=filter_is_read,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def update_computer(
    computer_id: int,
    computer: ComputerUpdate,
    db: DbSession,
    _user = Depends(require_permission("UPDATE_COMPUTER")),
):
    existing_computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if existing_computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )
    if computer_service.has_identity_conflict(
        db,
        computer_id,
        computer.hostname,
        computer.mac_address,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hostname or MAC address already belongs to another computer.",
        )

    try:

        computer =  computer_service.update_computer(
            db,
            existing_computer,
            computer,
        )

        audit_service.log_action(
            db=db,
            action="UPDATE_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

        return computer


    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Computer data conflicts with an existing computer.",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update computer.",
        )


@router.patch(
    "/{computer_id}",
    response_model=ComputerResponse,
)
def patch_computer(
    computer_id: int,
    computer: ComputerPatch,
    db: DbSession,
    _user = Depends(require_permission("UPDATE_COMPUTER")),
):
    existing_computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if existing_computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )

    if computer_service.has_patch_identity_conflict(
        db,
        computer_id,
        computer.hostname,
        computer.mac_address,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hostname or MAC address already belongs to another computer.",
        )

    try:
        computer = computer_service.patch_computer(
            db,
            existing_computer,
            computer,
        )

        audit_service.log_action(
            db=db,
            action="PATCH_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

        return computer



    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Computer data conflicts with an existing computer.",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update computer.",
        )



@router.delete(
    "/{computer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_computer(
    computer_id: int,
    db: DbSession,
    _user = Depends(require_permission("DELETE_COMPUTER")),
) -> None:
    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found.",
        )

    try:
        computer_service.delete_computer(
            db,
            computer,
        )

        audit_service.log_action(
            db=db,
            action="DELETE_COMPUTER",
            result=AuditResult.success,
            user_id=_user.id,
            target_type="computer",
            target_id=computer_id,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete computer.",
        )


# @router.post(
#     "/heartbeat",
#     status_code=status.HTTP_200_OK
# )
# def heartbeat(
#     agent_credential: AgentCredential = Depends(get_current_agent)
# ):

#     # if agent_credential.computer_id is None:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_400_BAD_REQUEST,
#     #         detail="The credential has not completed registration yet."
#     #     )

#     # computer = computer_service.get_computer_by_id(db, agent_credential.computer_id)

#     # if computer is None:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_404_NOT_FOUND,
#     #         detail="Computer is not found",
#     #     )

#     # try:
#     #     return computer_service.record_heartbeat(db, computer)
#     # except:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#     #         detail="Failed to record heartbeat",
#     #     )

#     # Kept temporarily as a lightweight "am I still authenticated" check.
#     # Will be replaced by POST /api/v1/metrics once metrics upload is built.
#     return {"message": "Credential valid"}

@router.post(
    "/heartbeat",
    status_code=status.HTTP_200_OK
)
def heartbeat(
    db: DbSession,
    agent_credential: AgentCredential = Depends(get_current_agent)
):
    if agent_credential.computer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This credential has not completed registration yet.",
        )

    agent_credential.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Credential valid"}
