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
)
from app.database import get_db
from app.models.agent_credential import AgentCredential
from app.models.issue import (
    IssueSeverity,
    IssueStatus,
    IssueSource,
)
from app.schemas.issue_schema import (
    IssueAgentCreate,
    IssueCreate,
    IssueResponse,
    IssueUpdate,
)
from app.services import (
    computer_service,
    issue_service,
)


DbSession = Annotated[
    Session,
    Depends(get_db),
]


router = APIRouter(
    prefix="/issues",
    tags=["Issue Management"],
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
def create_issue(
    issue_data: IssueCreate,
    db: DbSession,
    user=Depends(
        require_permission("UPDATE_COMPUTER")
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
        return issue_service.create_issue(
            db=db,
            issue_data=issue_data,
            created_by=user.id,
        )

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
def create_agent_issue(
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
    )

    try:
        return issue_service.create_issue(
            db=db,
            issue_data=create_data,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save agent issue",
        )


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
)
def update_issue(
    issue_id: int,
    issue_data: IssueUpdate,
    db: DbSession,
    user=Depends(
        require_permission("UPDATE_COMPUTER")
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
        return issue_service.update_issue(
            db=db,
            issue=issue,
            issue_data=issue_data,
            user_id=user.id,
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue",
        )


@router.post(
    "/{issue_id}/resolve",
    response_model=IssueResponse,
)
def resolve_issue(
    issue_id: int,
    db: DbSession,
    resolution_notes: str | None = None,
    user=Depends(
        require_permission("UPDATE_COMPUTER")
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
        return issue_service.resolve_issue(
            db=db,
            issue=issue,
            resolution_notes=resolution_notes,
            user_id=user.id,
        )

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
        require_permission("DELETE_COMPUTER")
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