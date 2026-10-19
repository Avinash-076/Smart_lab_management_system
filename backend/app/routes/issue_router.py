from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.auth import (
    get_current_agent,
    require_permission,
    require_any_permission,
)
from app.database import get_db
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditResult
from app.models.issue import (
    IssueSeverity,
    IssueStatus,
    IssueSource,
)
from app.schemas.issue_schema import (
    IssueAgentCreate,
    IssueAgentRecover,
    IssueCreate,
    IssueResolve,
    IssueResponse,
    IssueStatsResponse,
    IssueUpdate,
)
from app.services import (
    audit_service,
    computer_service,
    issue_service,
)
from app.websocket.connection_manager import manager


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/issues",
    tags=["Issue Management"],
)


@router.get(
    "/stats",
    response_model=IssueStatsResponse,
)
def get_issue_stats(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    computer_id: int | None = Query(
        default=None,
        gt=0,
    ),
):
    if computer_id is not None:
        computer = computer_service.get_computer_by_id(db, computer_id)
        if computer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Computer not found",
            )

    return issue_service.get_issue_stats(
        db=db,
        computer_id=computer_id,
    )


@router.get(
    "",
    response_model=list[IssueResponse],
)
def get_issues(
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
    computer_id: int | None = Query(
        default=None,
        gt=0,
    ),
    issue_status: IssueStatus | None = Query(
        default=None,
        alias="status",
    ),
    severity: IssueSeverity | None = None,
    search: str | None = Query(
        default=None,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):

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
    "/{issue_id}",
    response_model=IssueResponse,
)
def get_issue(
    issue_id: int,
    db: DbSession,
    _user=Depends(
        require_permission("VIEW_COMPUTERS")
    ),
):

    issue = issue_service.get_issue_by_id(
        db,
        issue_id,
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    return issue



@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    issue_data: IssueCreate,
    db: DbSession,
    user=Depends(
        require_any_permission("MANAGE_ISSUES", "UPDATE_COMPUTER")
    ),
):

    computer = computer_service.get_computer_by_id(
        db,
        issue_data.computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    try:
        created = issue_service.create_issue(
            db=db,
            issue_data=issue_data,
            created_by=user.id,
        )
        try:
            await manager.broadcast_to_dashboards(
                {
                    "type": "issue_created",
                    "computer_id": created.computer_id,
                    "computer_hostname": computer.hostname,
                    "issue": {
                        "id": created.id,
                        "computer_id": created.computer_id,
                        "computer_hostname": computer.hostname,
                        "title": created.title,
                        "description": created.description,
                        "severity": created.severity.value if hasattr(created.severity, "value") else str(created.severity),
                        "status": created.status.value if hasattr(created.status, "value") else str(created.status),
                        "source": created.source.value if hasattr(created.source, "value") else str(created.source),
                        "created_at": created.created_at.isoformat() if created.created_at else None,
                    },
                }
            )
        except Exception:
            pass
        return created

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create issue",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save issue",
        )


@router.post(
    "/agent",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_issue(
    issue_data: IssueAgentCreate,
    db: DbSession,
    agent_credential: AgentCredential = Depends(
        get_current_agent
    ),
):

    computer_id = agent_credential.computer_id

    if computer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not associated with a computer",
        )

    computer = computer_service.get_computer_by_id(
        db,
        computer_id,
    )

    if computer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Computer not found",
        )

    create_data = IssueCreate(
        computer_id=computer_id,
        title=issue_data.title,
        description=issue_data.description,
        severity=issue_data.severity,
        source=IssueSource.agent,
        idempotency_key=issue_data.idempotency_key,
    )

    try:
        created = issue_service.create_issue(
            db=db,
            issue_data=create_data,
        )
        try:
            audit_service.log_action(
                db=db,
                result=AuditResult.success,
                action="AGENT_ISSUE_CREATED",
                target_type="Issue",
                target_id=created.id,
            )
        except Exception:
            pass
        try:
            await manager.broadcast_to_dashboards(
                {
                    "type": "issue_created",
                    "computer_id": created.computer_id,
                    "computer_hostname": computer.hostname,
                    "issue": {
                        "id": created.id,
                        "computer_id": created.computer_id,
                        "computer_hostname": computer.hostname,
                        "title": created.title,
                        "description": created.description,
                        "severity": created.severity.value if hasattr(created.severity, "value") else str(created.severity),
                        "status": created.status.value if hasattr(created.status, "value") else str(created.status),
                        "source": created.source.value if hasattr(created.source, "value") else str(created.source),
                        "created_at": created.created_at.isoformat() if created.created_at else None,
                    },
                }
            )
        except Exception:
            pass
        return created

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create agent issue",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save agent issue",
        )


@router.post(
    "/agent/recover",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def recover_agent_issue(
    recovery_data: IssueAgentRecover,
    db: DbSession,
    agent_credential: AgentCredential = Depends(
        get_current_agent
    ),
):
    """
    Agent endpoint to record automated recovery (e.g. device disconnected).
    Guarantees agent can only modify issues for its own authenticated computer.
    """
    computer_id = agent_credential.computer_id
    if computer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not associated with a computer",
        )

    issue = issue_service.recover_agent_issue(
        db=db,
        computer_id=computer_id,
        idempotency_key=recovery_data.idempotency_key,
        title=recovery_data.title,
        recovery_notes=recovery_data.recovery_notes,
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active issue not found for recovery",
        )

    try:
        audit_service.log_action(
            db=db,
            result=AuditResult.success,
            action="AGENT_ISSUE_RECOVERED",
            target_type="Issue",
            target_id=issue.id,
        )
    except Exception:
        pass

    try:
        await manager.broadcast_to_dashboards(
            {
                "type": "issue_resolved",
                "computer_id": issue.computer_id,
                "issue_id": issue.id,
                "title": issue.title,
                "status": "resolved",
                "resolution_notes": issue.resolution_notes,
                "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
            }
        )
    except Exception:
        pass

    return issue


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
)
async def update_issue(
    issue_id: int,
    issue_data: IssueUpdate,
    db: DbSession,
    user=Depends(
        require_any_permission("MANAGE_ISSUES", "UPDATE_COMPUTER")
    ),
):

    issue = issue_service.get_issue_by_id(
        db,
        issue_id,
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    try:
        updated = issue_service.update_issue(
            db=db,
            issue=issue,
            issue_data=issue_data,
            user_id=user.id,
        )
        try:
            await manager.broadcast_to_dashboards(
                {
                    "type": "issue_updated",
                    "computer_id": updated.computer_id,
                    "issue_id": updated.id,
                    "title": updated.title,
                    "status": updated.status.value if hasattr(updated.status, "value") else str(updated.status),
                    "severity": updated.severity.value if hasattr(updated.severity, "value") else str(updated.severity),
                }
            )
        except Exception:
            pass
        return updated

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue",
        )


@router.post(
    "/{issue_id}/resolve",
    response_model=IssueResponse,
)
async def resolve_issue(
    issue_id: int,
    db: DbSession,
    resolve_data: IssueResolve | None = None,
    resolution_notes: str | None = None,
    user=Depends(
        require_any_permission("MANAGE_ISSUES", "UPDATE_COMPUTER")
    ),
):

    issue = issue_service.get_issue_by_id(
        db,
        issue_id,
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    notes = None
    if resolve_data and resolve_data.resolution_notes:
        notes = resolve_data.resolution_notes
    elif resolution_notes:
        notes = resolution_notes

    try:
        resolved = issue_service.resolve_issue(
            db=db,
            issue=issue,
            resolution_notes=notes,
            user_id=user.id,
        )
        try:
            await manager.broadcast_to_dashboards(
                {
                    "type": "issue_resolved",
                    "computer_id": resolved.computer_id,
                    "issue_id": resolved.id,
                    "title": resolved.title,
                    "status": "resolved",
                    "resolution_notes": resolved.resolution_notes,
                    "resolved_at": resolved.resolved_at.isoformat() if resolved.resolved_at else None,
                }
            )
        except Exception:
            pass
        return resolved

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve issue",
        )


@router.delete(
    "/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_issue(
    issue_id: int,
    db: DbSession,
    _user=Depends(
        require_any_permission("MANAGE_ISSUES", "DELETE_COMPUTER")
    ),
):

    issue = issue_service.get_issue_by_id(
        db,
        issue_id,
    )

    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    try:
        issue_service.delete_issue(
            db,
            issue,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete issue",
        )